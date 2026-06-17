"""Checkpoint CRUD and listing for admin UI."""

from fastapi import HTTPException

from ...auth import AuthContext, assert_admin_tenant_access
from ...db import get_db_connection
from ...models import CheckpointCreateRequest, CheckpointMetadataUpdate
from ...services.admin_responses import admin_mutation
from ...services.dsl import validate_expression
from ...services.pagination import MAX_PAGE_SIZE, clamp_pagination
from ...services.resource_lifecycle import assert_not_current_checkpoint
from ...services.templates import extract_placeholders_from_text
from ...types import OptionalUuidStr, UuidStr
from .common import collect_all_pages, raise_admin_error


def _validate_checkpoint_dsl(dsl_expression: str, signal_ids: list[str], cur) -> None:
    signal_names: list[str] = []
    if signal_ids:
        cur.execute(
            "SELECT name FROM signals WHERE id = ANY(%s::uuid[])",
            (signal_ids,),
        )
        signal_names = [row[0] for row in cur.fetchall()]
    result = validate_expression(dsl_expression, signal_names, "strict")
    if not result.ok:
        raise HTTPException(status_code=422, detail="; ".join(result.errors))


def _resolve_checkpoint_signal_ids(cur, payload: CheckpointCreateRequest) -> list[str]:
    signal_ids = list(payload.signal_ids)
    if signal_ids:
        return signal_ids
    if not payload.copy_from_checkpoint_id:
        return []
    cur.execute(
        """
        SELECT DISTINCT ON (linked.name)
               COALESCE(scv.signal_id, linked.signal_id)
          FROM (
                SELECT s.name, s.id AS signal_id, s.tenant_id, cs.created_at
                  FROM checkpoint_signals cs
                  JOIN signals s ON s.id = cs.signal_id
                 WHERE cs.checkpoint_id = %s
          ) linked
     LEFT JOIN signal_current_version scv
            ON scv.tenant_id = linked.tenant_id
           AND scv.name = linked.name
      ORDER BY linked.name, linked.created_at DESC
        """,
        (payload.copy_from_checkpoint_id,),
    )
    return [str(row[0]) for row in cur.fetchall()]


def _assert_signals_same_tenant(cur, tenant_id: str, signal_ids: list[str]) -> None:
    if not signal_ids:
        return
    cur.execute(
        """
        SELECT id FROM signals
         WHERE id = ANY(%s::uuid[])
           AND tenant_id = %s
        """,
        (signal_ids, tenant_id),
    )
    found = {str(row[0]) for row in cur.fetchall()}
    missing = [sid for sid in signal_ids if sid not in found]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Signals not found for tenant: {', '.join(missing)}",
        )


def _assert_unique_logical_signal_names(cur, signal_ids: list[str]) -> None:
    if not signal_ids:
        return
    if len(signal_ids) != len(set(signal_ids)):
        raise HTTPException(
            status_code=409,
            detail="Checkpoint cannot link the same signal more than once.",
        )
    cur.execute(
        """
        SELECT name
          FROM signals
         WHERE id = ANY(%s::uuid[])
         GROUP BY name
        HAVING COUNT(*) > 1
        """,
        (signal_ids,),
    )
    duplicates = [row[0] for row in cur.fetchall()]
    if duplicates:
        raise HTTPException(
            status_code=409,
            detail=(
                "Checkpoint cannot link multiple versions of the same signal: "
                + ", ".join(sorted(duplicates))
            ),
        )


def create_checkpoint(payload: CheckpointCreateRequest) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        signal_ids = _resolve_checkpoint_signal_ids(cur, payload)
        _assert_signals_same_tenant(cur, payload.tenant_id, signal_ids)
        _assert_unique_logical_signal_names(cur, signal_ids)
        _validate_checkpoint_dsl(payload.dsl_expression, signal_ids, cur)

        cur.execute(
            """
            INSERT INTO checkpoints (
                tenant_id, name, description, type, dsl_expression,
                method_of_call, max_cost, override_cost_flag, timeout_seconds
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                payload.tenant_id,
                payload.name,
                payload.description,
                payload.type,
                payload.dsl_expression,
                payload.method_of_call,
                payload.max_cost,
                payload.override_cost_flag,
                payload.timeout_seconds,
            ),
        )

        new_checkpoint_id = str(cur.fetchone()[0])
        association_count = 0
        for signal_id in signal_ids:
            cur.execute(
                """
                INSERT INTO checkpoint_signals (checkpoint_id, signal_id)
                VALUES (%s, %s)
                """,
                (new_checkpoint_id, signal_id),
            )
            association_count += 1

        conn.commit()
        return admin_mutation(
            "created",
            new_checkpoint_id,
            association_count=association_count,
        )

    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="create_checkpoint failed")
    finally:
        cur.close()
        conn.close()


def list_checkpoints(
    *,
    scoped_tenant_id: OptionalUuidStr = None,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
) -> dict:
    page, size = clamp_pagination(page, size)
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        base_query = """
            SELECT c.id, c.tenant_id, c.name, c.description, c.type, c.dsl_expression,
                   c.method_of_call, c.max_cost, c.override_cost_flag, c.timeout_seconds,
                   c.created_at, c.updated_at,
                   t.name as tenant_name,
                   COALESCE(
                       (SELECT json_agg(json_build_object(
                           'id', s.id,
                           'name', s.name,
                           'type', s.type,
                           'method_of_call', s.method_of_call,
                           'cost', s.cost,
                           'timeout_seconds', s.timeout_seconds
                       ))
                       FROM checkpoint_signals cs
                       JOIN signals s ON cs.signal_id = s.id
                       WHERE cs.checkpoint_id = c.id), '[]'
                   ) as signals,
                   CASE 
                       WHEN cv.checkpoint_id IS NOT NULL THEN true 
                       ELSE false 
                   END as is_current_version,
                   EXISTS (
                       SELECT 1
                         FROM checkpoint_current_version cvn
                        WHERE cvn.tenant_id = c.tenant_id
                          AND cvn.name = c.name
                   ) as name_has_current_version
            FROM checkpoints c
            LEFT JOIN tenants t ON c.tenant_id = t.id
            LEFT JOIN checkpoint_current_version cv ON cv.checkpoint_id = c.id
            """

        where_clause = []
        params = []

        if scoped_tenant_id:
            where_clause.append("c.tenant_id = %s")
            params.append(scoped_tenant_id)

        if active_only:
            where_clause.append("cv.checkpoint_id IS NOT NULL")

        if where_clause:
            base_query += " WHERE " + " AND ".join(where_clause)

        base_query += " ORDER BY c.name ASC, c.id ASC"

        count_query = f"SELECT COUNT(*) FROM ({base_query}) as count_query"
        cur.execute(count_query, params)
        total = cur.fetchone()[0]

        paginated_query = base_query + " LIMIT %s OFFSET %s"
        params.extend([size, (page - 1) * size])
        cur.execute(paginated_query, params)

        checkpoints = []
        for row in cur.fetchall():
            checkpoint = {
                "id": str(row[0]),
                "tenant_id": str(row[1]),
                "name": row[2],
                "description": row[3],
                "type": row[4],
                "dsl_expression": row[5],
                "method_of_call": row[6],
                "max_cost": row[7],
                "override_cost_flag": row[8],
                "timeout_seconds": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
                "updated_at": row[11].isoformat() if row[11] else None,
                "tenant_name": row[12],
                "signals": row[13],
                "is_current_version": row[14],
                "name_has_current_version": row[15],
                "param_placeholders": extract_placeholders_from_text(row[5]) if row[5] else [],
            }
            checkpoints.append(checkpoint)

        return {
            "items": checkpoints,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": (total + size - 1) // size,
        }

    except Exception as e:
        raise_admin_error(e, context="list_checkpoints failed")
    finally:
        cur.close()
        conn.close()


def list_all_checkpoints(
    *,
    scoped_tenant_id: OptionalUuidStr = None,
    active_only: bool = False,
) -> list:
    return collect_all_pages(
        lambda page: list_checkpoints(
            scoped_tenant_id=scoped_tenant_id,
            page=page,
            size=MAX_PAGE_SIZE,
            active_only=active_only,
        )
    )


def get_checkpoint(checkpoint_id: UuidStr, *, auth: AuthContext) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.tenant_id, c.name, c.description, c.type, c.dsl_expression,
                   c.method_of_call, c.max_cost, c.override_cost_flag, c.timeout_seconds,
                   CASE WHEN cv.checkpoint_id IS NOT NULL THEN true ELSE false END,
                   EXISTS (
                       SELECT 1
                         FROM checkpoint_current_version cvn
                        WHERE cvn.tenant_id = c.tenant_id
                          AND cvn.name = c.name
                   )
              FROM checkpoints c
              LEFT JOIN checkpoint_current_version cv ON cv.checkpoint_id = c.id
             WHERE c.id = %s
            """,
            (checkpoint_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
        assert_admin_tenant_access(auth, str(row[1]))
        return {
            "id": str(row[0]),
            "tenant_id": str(row[1]),
            "name": row[2],
            "description": row[3],
            "type": row[4],
            "dsl_expression": row[5],
            "method_of_call": row[6],
            "max_cost": row[7],
            "override_cost_flag": row[8],
            "timeout_seconds": row[9],
            "is_current_version": row[10],
            "name_has_current_version": row[11],
        }
    finally:
        conn.close()


def update_checkpoint(checkpoint_id: UuidStr, payload: CheckpointMetadataUpdate) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE checkpoints
               SET description = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (payload.description, checkpoint_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
        conn.commit()
        return admin_mutation("updated", checkpoint_id)
    finally:
        conn.close()


def delete_checkpoint(checkpoint_id: UuidStr) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        assert_not_current_checkpoint(cur, checkpoint_id)
        cur.execute("DELETE FROM checkpoints WHERE id = %s", (checkpoint_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
        conn.commit()
        return admin_mutation("deleted", checkpoint_id)
    finally:
        conn.close()
