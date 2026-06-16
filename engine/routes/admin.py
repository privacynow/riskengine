from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..auth import AuthContext, require_admin, resolve_admin_tenant_id
from ..config import logger
from ..db import db_cursor, get_db_connection
from ..models import (
    AdminTestDecisionRequest,
    CheckpointCreateRequest,
    CheckpointMetadataUpdate,
    CheckpointSignalCreateUpdate,
    DecisionRequest,
    DecisionResponse,
    DslPreflightRequest,
    PromotionRequest,
    SignalCreateUpdate,
    SignalMetadataUpdate,
    TenantCreateUpdate,
    VariableValueCreateUpdate,
)
from ..services.dsl import validate_expression
from ..services.dsl_preflight import preflight_dsl
from ..services.promotion_audit import (
    normalize_promotion_reason,
    record_promotion_audit,
)
from ..services.admin_responses import admin_mutation
from ..services.decision import execute_decision
from ..services.pagination import build_paginated_response, paginate_query
from ..services.security import (
    admin_signal_secret_fields,
    contains_embedded_credential,
    has_bearer_token_value,
    redact_param_map_for_response,
    redact_template_for_response,
    resolve_bearer_token_for_persist,
)
from ..services.templates import extract_placeholders_from_text
from ..types import UuidStr

router = APIRouter(tags=["admin"], dependencies=[Depends(require_admin)])

GENERIC_ADMIN_ERROR = "An internal error occurred."


def raise_admin_error(exc: Exception, *, context: str) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("%s", context)
    raise HTTPException(status_code=500, detail=GENERIC_ADMIN_ERROR) from exc

def _validate_signal_templates(payload: SignalCreateUpdate) -> None:
    checks = (
        ("request_headers_template", payload.request_headers_template),
        ("request_body_template", payload.request_body_template),
        ("request_url_params_template", payload.request_url_params_template),
        ("function_params_template", payload.function_params_template),
    )
    for field_name, value in checks:
        if contains_embedded_credential(value):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{field_name} must not embed credentials; "
                    "store outbound auth in bearer_token only."
                ),
            )


def _signal_placeholders_from_row(r) -> list:
    placeholders = extract_placeholders_from_text(r[13]) \
        + extract_placeholders_from_text(r[14]) \
        + extract_placeholders_from_text(r[15]) \
        + extract_placeholders_from_text(r[19])
    return sorted(set(placeholders))


def _admin_signal_item_from_row(r, *, include_current: bool) -> dict:
    item = {
        "id": str(r[0]),
        "tenant_id": str(r[1]),
        "name": r[2],
        "description": r[3],
        "type": r[4],
        "method_of_call": r[5],
        "expression_body": r[6],
        "cost": r[7],
        "cache_expiration_seconds": r[8],
        "timeout_seconds": r[9],
        "can_run_in_parallel": r[10],
        "order_of_evaluation": r[11],
        "http_method": r[12],
        "request_url_params_template": redact_template_for_response(r[13]),
        "request_body_template": redact_template_for_response(r[14]),
        "request_headers_template": redact_template_for_response(r[15]),
        **admin_signal_secret_fields(r[16]),
        "allow_caching": r[17],
        "global_reuse": r[18],
        "function_params_template": redact_template_for_response(r[19]),
        "param_placeholders": _signal_placeholders_from_row(r),
    }
    if include_current:
        item["is_current_version"] = r[20]
    return item


def _resolve_signal_bearer_token(cur, payload: SignalCreateUpdate) -> str | None:
    if has_bearer_token_value(payload.bearer_token):
        return payload.bearer_token.strip()
    cur.execute(
        """
        SELECT bearer_token
          FROM signals
         WHERE tenant_id = %s AND name = %s
         ORDER BY updated_at DESC
         LIMIT 1
        """,
        (payload.tenant_id, payload.name),
    )
    row = cur.fetchone()
    return row[0] if row else None


@router.post("/ui/test_decisions", response_model=DecisionResponse)
async def admin_test_decision(
    payload: AdminTestDecisionRequest,
    auth: AuthContext = Depends(require_admin),
):
    """Run a checkpoint decision for a tenant without exposing runtime tokens to the client."""
    resolve_admin_tenant_id(auth, payload.tenant_id, required=True)
    decision_request = DecisionRequest(
        checkpoint_name=payload.checkpoint_name,
        applicant_id=payload.applicant_id,
        correlation_id=payload.correlation_id,
        parameters=payload.parameters,
    )
    with db_cursor() as (conn, cur):
        return await execute_decision(
            conn,
            cur,
            payload.tenant_id,
            decision_request,
            actor_id=auth.actor_id,
            checkpoint_id=payload.checkpoint_id,
        )


@router.post("/ui/tenants")
def create_tenant(payload: TenantCreateUpdate):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create new tenant
        cur.execute(
            "INSERT INTO tenants (name) VALUES (%s) RETURNING id",
            (payload.name,)
        )
        new_tenant_id = cur.fetchone()[0]
        
        # If copying from existing tenant
        if payload.copy_from_tenant_id:
            cur.execute(
                """
                SELECT c.id, c.name, c.description, c.type, c.dsl_expression,
                       c.method_of_call, c.max_cost, c.override_cost_flag, c.timeout_seconds
                  FROM checkpoints c
                  JOIN checkpoint_current_version cv
                    ON c.id = cv.checkpoint_id AND c.tenant_id = cv.tenant_id
                 WHERE c.tenant_id = %s
                """,
                (payload.copy_from_tenant_id,),
            )
            checkpoint_mappings: dict[str, str] = {}
            for old_id, name, description, cp_type, dsl, method, max_cost, override, timeout in cur.fetchall():
                cur.execute(
                    """
                    INSERT INTO checkpoints (
                        tenant_id, name, description, type, dsl_expression,
                        method_of_call, max_cost, override_cost_flag, timeout_seconds
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        new_tenant_id,
                        name,
                        description,
                        cp_type,
                        dsl,
                        method,
                        max_cost,
                        override,
                        timeout,
                    ),
                )
                new_cp_id = cur.fetchone()[0]
                checkpoint_mappings[str(old_id)] = str(new_cp_id)
                cur.execute(
                    """
                    INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
                    VALUES (%s, %s, %s)
                    """,
                    (new_tenant_id, name, new_cp_id),
                )

            cur.execute(
                """
                SELECT s.id, s.name, s.description, s.type, s.method_of_call,
                       s.expression_body, s.cost, s.cache_expiration_seconds, s.timeout_seconds,
                       s.can_run_in_parallel, s.order_of_evaluation, s.http_method,
                       s.request_url_params_template, s.request_body_template,
                       s.request_headers_template, s.allow_caching, s.global_reuse,
                       s.function_params_template
                  FROM signals s
                  JOIN signal_current_version cv
                    ON s.id = cv.signal_id AND s.tenant_id = cv.tenant_id
                 WHERE s.tenant_id = %s
                """,
                (payload.copy_from_tenant_id,),
            )
            signal_name_to_new_id: dict[str, str] = {}
            for row in cur.fetchall():
                (
                    old_sig_id,
                    name,
                    description,
                    sig_type,
                    method_of_call,
                    expression_body,
                    cost,
                    cache_expiration_seconds,
                    timeout_seconds,
                    can_run_in_parallel,
                    order_of_evaluation,
                    http_method,
                    request_url_params_template,
                    request_body_template,
                    request_headers_template,
                    allow_caching,
                    global_reuse,
                    function_params_template,
                ) = row
                cur.execute(
                    """
                    INSERT INTO signals (
                        tenant_id, name, description, type, method_of_call,
                        expression_body, cost, cache_expiration_seconds, timeout_seconds,
                        can_run_in_parallel, order_of_evaluation, http_method,
                        request_url_params_template, request_body_template,
                        request_headers_template, bearer_token, allow_caching,
                        global_reuse, function_params_template
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        new_tenant_id,
                        name,
                        description,
                        sig_type,
                        method_of_call,
                        expression_body,
                        cost,
                        cache_expiration_seconds,
                        timeout_seconds,
                        can_run_in_parallel,
                        order_of_evaluation,
                        http_method,
                        request_url_params_template,
                        request_body_template,
                        request_headers_template,
                        allow_caching,
                        global_reuse,
                        function_params_template,
                    ),
                )
                new_sig_id = cur.fetchone()[0]
                signal_name_to_new_id[name] = str(new_sig_id)
                cur.execute(
                    """
                    INSERT INTO signal_current_version (tenant_id, name, signal_id)
                    VALUES (%s, %s, %s)
                    """,
                    (new_tenant_id, name, new_sig_id),
                )

            for old_cp_id, new_cp_id in checkpoint_mappings.items():
                cur.execute(
                    """
                    SELECT DISTINCT s.name
                      FROM checkpoint_signals cs
                      JOIN signals s ON s.id = cs.signal_id
                     WHERE cs.checkpoint_id = %s::uuid
                    """,
                    (old_cp_id,),
                )
                for (linked_signal_name,) in cur.fetchall():
                    new_sig_id = signal_name_to_new_id.get(linked_signal_name)
                    if not new_sig_id:
                        continue
                    cur.execute(
                        """
                        INSERT INTO checkpoint_signals (checkpoint_id, signal_id)
                        SELECT %s::uuid, %s::uuid
                         WHERE NOT EXISTS (
                            SELECT 1 FROM checkpoint_signals
                             WHERE checkpoint_id = %s::uuid AND signal_id = %s::uuid
                         )
                        """,
                        (new_cp_id, new_sig_id, new_cp_id, new_sig_id),
                    )

            for signal_name, new_sig_id in signal_name_to_new_id.items():
                cur.execute(
                    """
                    INSERT INTO signal_variable_values (signal_id, name, value)
                    SELECT DISTINCT ON (svv.name) %s::uuid, svv.name, svv.value
                      FROM signal_variable_values svv
                      JOIN signals s ON s.id = svv.signal_id
                     WHERE s.tenant_id = %s AND s.name = %s
                     ORDER BY svv.name, svv.updated_at DESC
                    ON CONFLICT (signal_id, name) DO NOTHING
                    """,
                    (new_sig_id, payload.copy_from_tenant_id, signal_name),
                )
        
        conn.commit()
        return admin_mutation("created", new_tenant_id)
    
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="create_tenant failed")
    finally:
        cur.close()
        conn.close()


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
        SELECT signal_id FROM checkpoint_signals
         WHERE checkpoint_id = %s
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


@router.post("/ui/checkpoints")
def create_checkpoint(payload: CheckpointCreateRequest):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        signal_ids = _resolve_checkpoint_signal_ids(cur, payload)
        _assert_signals_same_tenant(cur, payload.tenant_id, signal_ids)
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


@router.post("/ui/signals")
def create_signal(payload: SignalCreateUpdate):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        _validate_signal_templates(payload)
        if payload.type == "expression" and payload.expression_body:
            result = validate_expression(
                payload.expression_body,
                [],
                "warn_unknown",
            )
            if not result.ok:
                raise HTTPException(status_code=422, detail="; ".join(result.errors))
        bearer_token = _resolve_signal_bearer_token(cur, payload)
        # Create new signal version
        cur.execute("""
            INSERT INTO signals (
                tenant_id, name, description, type, method_of_call,
                expression_body, cost, cache_expiration_seconds, timeout_seconds,
                can_run_in_parallel, order_of_evaluation, http_method,
                request_url_params_template, request_body_template,
                request_headers_template, bearer_token, allow_caching,
                global_reuse, function_params_template
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            payload.tenant_id, payload.name, payload.description,
            payload.type, payload.method_of_call, payload.expression_body,
            payload.cost, payload.cache_expiration_seconds, payload.timeout_seconds,
            payload.can_run_in_parallel, payload.order_of_evaluation,
            payload.http_method, payload.request_url_params_template,
            payload.request_body_template, payload.request_headers_template,
            bearer_token, payload.allow_caching,
            payload.global_reuse, payload.function_params_template
        ))
        
        new_signal_id = cur.fetchone()[0]

        if payload.copy_from_signal_id:
            cur.execute(
                """
                SELECT tenant_id FROM signals WHERE id = %s
                """,
                (payload.copy_from_signal_id,),
            )
            source = cur.fetchone()
            if not source:
                raise HTTPException(status_code=404, detail="Source signal not found.")
            if str(source[0]) != payload.tenant_id:
                raise HTTPException(status_code=422, detail="Source signal tenant mismatch.")

            cur.execute(
                """
                INSERT INTO signal_variable_values (id, signal_id, name, value)
                SELECT uuid_generate_v4(), %s, name, value
                  FROM signal_variable_values
                 WHERE signal_id = %s
                """,
                (new_signal_id, payload.copy_from_signal_id),
            )
            cur.execute(
                """
                INSERT INTO checkpoint_signals (checkpoint_id, signal_id)
                SELECT checkpoint_id, %s
                  FROM checkpoint_signals
                 WHERE signal_id = %s
                """,
                (new_signal_id, payload.copy_from_signal_id),
            )

        conn.commit()
        return admin_mutation("created", new_signal_id)
    
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="create_signal failed")
    finally:
        cur.close()
        conn.close()


@router.get("/ui/tenants")
def list_tenants(page: int = 1, size: int = 10):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        base_query = "SELECT id, name FROM tenants"
        total, rows = paginate_query(cur, base_query, (), page, size)
        items = []
        for r in rows:
            items.append({"id": str(r[0]), "name": r[1]})
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@router.get("/ui/all_tenants")
def list_all_tenants():
    """Unpaginated tenant list for dropdowns and bulk admin views."""
    return list_tenants(page=1, size=10000)["items"]


@router.get("/ui/tenants/{tenant_id}")
def get_tenant(tenant_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM tenants WHERE id=%s", (tenant_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        return {"id": str(row[0]), "name": row[1]}
    finally:
        if conn:
            conn.close()


@router.put("/ui/tenants/{tenant_id}")
def update_tenant(tenant_id: UuidStr, payload: TenantCreateUpdate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE tenants
               SET name = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (payload.name, tenant_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        conn.commit()
        return admin_mutation("updated", tenant_id, name=payload.name)
    finally:
        if conn:
            conn.close()


@router.delete("/ui/tenants/{tenant_id}")
def delete_tenant(tenant_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        conn.commit()
        return admin_mutation("deleted", tenant_id)
    finally:
        if conn:
            conn.close()


@router.get("/ui/checkpoints")
def list_checkpoints(tenant_id: Optional[str] = None, page: int = 1, size: int = 10, active_only: bool = False):
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
                   END as is_current_version
            FROM checkpoints c
            LEFT JOIN tenants t ON c.tenant_id = t.id
            LEFT JOIN checkpoint_current_version cv ON cv.checkpoint_id = c.id
            """

        where_clause = []
        params = []

        if tenant_id:
            where_clause.append("c.tenant_id = %s")
            params.append(tenant_id)

        if active_only:
            where_clause.append("cv.checkpoint_id IS NOT NULL")

        if where_clause:
            base_query += " WHERE " + " AND ".join(where_clause)

        base_query += " ORDER BY c.name ASC, c.id ASC"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({base_query}) as count_query"
        cur.execute(count_query, params)
        total = cur.fetchone()[0]

        # Get paginated results
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
                "param_placeholders": extract_placeholders_from_text(row[5]) if row[5] else []
            }
            checkpoints.append(checkpoint)

        return {
            "items": checkpoints,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": (total + size - 1) // size
        }

    except Exception as e:
        raise_admin_error(e, context="list_checkpoints failed")
    finally:
        cur.close()
        conn.close()


@router.get("/ui/all_checkpoints")
def list_all_checkpoints(
    tenant_id: Optional[str] = None,
    active_only: bool = False,
):
    """Unpaginated checkpoint list for dropdowns and bulk admin views."""
    return list_checkpoints(
        tenant_id=tenant_id,
        page=1,
        size=10000,
        active_only=active_only,
    )["items"]


@router.get("/ui/checkpoints/{checkpoint_id}")
def get_checkpoint(checkpoint_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.tenant_id, c.name, c.description, c.type, c.dsl_expression,
                   c.method_of_call, c.max_cost, c.override_cost_flag, c.timeout_seconds,
                   CASE WHEN cv.checkpoint_id IS NOT NULL THEN true ELSE false END
              FROM checkpoints c
              LEFT JOIN checkpoint_current_version cv ON cv.checkpoint_id = c.id
             WHERE c.id = %s
            """,
            (checkpoint_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
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
        }
    finally:
        if conn:
            conn.close()


@router.put("/ui/checkpoints/{checkpoint_id}")
def update_checkpoint(checkpoint_id: UuidStr, payload: CheckpointMetadataUpdate):
    conn = None
    try:
        conn = get_db_connection()
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
        if conn:
            conn.close()


@router.delete("/ui/checkpoints/{checkpoint_id}")
def delete_checkpoint(checkpoint_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM checkpoints WHERE id = %s", (checkpoint_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
        conn.commit()
        return admin_mutation("deleted", checkpoint_id)
    finally:
        if conn:
            conn.close()


@router.get("/ui/signals")
def list_signals(checkpoint_id: Optional[str] = None,
                 tenant_id: Optional[str] = None,
                 page: int = 1,
                 size: int = 10,
                 active_only: bool = False):
    """
    If checkpoint_id is provided, returns signals associated with that checkpoint.
    If tenant_id is provided, returns signals for that tenant.
    Otherwise returns all signals.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if checkpoint_id:
            base_query = """
                SELECT s.id, s.tenant_id, s.name, s.description, s.type,
                       s.method_of_call, s.expression_body, s.cost,
                       s.cache_expiration_seconds, s.timeout_seconds,
                       s.can_run_in_parallel, s.order_of_evaluation,
                       s.http_method, s.request_url_params_template,
                       s.request_body_template, s.request_headers_template,
                       s.bearer_token, s.allow_caching, s.global_reuse,
                       s.function_params_template,
                       CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version
                  FROM signals s
                  JOIN checkpoint_signals cs ON cs.signal_id = s.id
                  LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
                 WHERE cs.checkpoint_id = %s
            """
            params = [checkpoint_id]
            if active_only:
                base_query += " AND scv.signal_id IS NOT NULL"
        elif tenant_id:
            base_query = """
                SELECT s.id, s.tenant_id, s.name, s.description, s.type,
                       s.method_of_call, s.expression_body, s.cost,
                       s.cache_expiration_seconds, s.timeout_seconds,
                       s.can_run_in_parallel, s.order_of_evaluation,
                       s.http_method, s.request_url_params_template,
                       s.request_body_template, s.request_headers_template,
                       s.bearer_token, s.allow_caching, s.global_reuse,
                       s.function_params_template,
                       CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version
                  FROM signals s
                  LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
                 WHERE s.tenant_id = %s
            """
            params = [tenant_id]
            if active_only:
                base_query += " AND scv.signal_id IS NOT NULL"
        else:
            base_query = """
                SELECT s.id, s.tenant_id, s.name, s.description, s.type,
                       s.method_of_call, s.expression_body, s.cost,
                       s.cache_expiration_seconds, s.timeout_seconds,
                       s.can_run_in_parallel, s.order_of_evaluation,
                       s.http_method, s.request_url_params_template,
                       s.request_body_template, s.request_headers_template,
                       s.bearer_token, s.allow_caching, s.global_reuse,
                       s.function_params_template,
                       CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version
                  FROM signals s
                  LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
            """
            params = []
            if active_only:
                base_query += " WHERE scv.signal_id IS NOT NULL"

        base_query += " ORDER BY s.name ASC, s.id ASC"

        total, rows = paginate_query(cur, base_query, params, page, size)
        items = [_admin_signal_item_from_row(r, include_current=True) for r in rows]

        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@router.get("/ui/all_signals")
def list_all_signals(
    tenant_id: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
    active_only: bool = False,
):
    """Unpaginated signal list for dropdowns and bulk admin views."""
    return list_signals(
        checkpoint_id=checkpoint_id,
        tenant_id=tenant_id,
        page=1,
        size=10000,
        active_only=active_only,
    )["items"]


@router.get("/ui/signals/{signal_id}")
def get_signal(signal_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id, s.tenant_id, s.name, s.description, s.type, s.method_of_call,
                   s.expression_body, s.cost, s.cache_expiration_seconds,
                   s.timeout_seconds, s.can_run_in_parallel, s.order_of_evaluation,
                   s.http_method, s.request_url_params_template,
                   s.request_body_template, s.request_headers_template,
                   s.bearer_token, s.allow_caching, s.global_reuse,
                   s.function_params_template,
                   CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END AS is_current_version
              FROM signals s
              LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
             WHERE s.id = %s
            """,
            (signal_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Signal not found.")

        return _admin_signal_item_from_row(row, include_current=True)
    finally:
        if conn:
            conn.close()


@router.put("/ui/signals/{signal_id}")
def update_signal(signal_id: UuidStr, payload: SignalMetadataUpdate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE signals
               SET description = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (payload.description, signal_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Signal not found.")
        conn.commit()
        return admin_mutation("updated", signal_id)
    finally:
        if conn:
            conn.close()


@router.delete("/ui/signals/{signal_id}")
def delete_signal(signal_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM signals WHERE id = %s", (signal_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Signal not found.")
        conn.commit()
        return admin_mutation("deleted", signal_id)
    finally:
        if conn:
            conn.close()


@router.post("/ui/variable_values")
def create_variable_value(payload: VariableValueCreateUpdate):
    """Create or update a row in signal_variable_values for a variable signal."""
    conn = None
    try:
        new_id = str(uuid.uuid4())
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO signal_variable_values (id, signal_id, name, value)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (signal_id, name) DO UPDATE
               SET value = EXCLUDED.value,
                   updated_at = NOW()
            RETURNING id
            """,
            (new_id, payload.signal_id, payload.name, payload.value),
        )
        row_id = str(cur.fetchone()[0])
        conn.commit()
        return admin_mutation("created", row_id)
    finally:
        if conn:
            conn.close()


@router.get("/ui/variable_values/{variable_value_id}")
def get_variable_value_item(variable_value_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, signal_id, name, value
              FROM signal_variable_values
             WHERE id = %s
            """,
            (variable_value_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Variable value not found.")
        return {
            "id": str(row[0]),
            "signal_id": str(row[1]),
            "name": row[2],
            "value": row[3],
        }
    finally:
        if conn:
            conn.close()


@router.put("/ui/variable_values/{variable_value_id}")
def update_variable_value(variable_value_id: UuidStr, payload: VariableValueCreateUpdate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE signal_variable_values
               SET signal_id = %s,
                   name = %s,
                   value = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (
                payload.signal_id,
                payload.name,
                payload.value,
                variable_value_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Variable value not found.")
        conn.commit()
        return admin_mutation("updated", variable_value_id)
    finally:
        if conn:
            conn.close()


@router.delete("/ui/variable_values/{variable_value_id}")
def delete_variable_value(variable_value_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM signal_variable_values WHERE id = %s", (variable_value_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Variable value not found.")
        conn.commit()
        return admin_mutation("deleted", variable_value_id)
    finally:
        if conn:
            conn.close()


@router.post("/ui/checkpoint_signals")
def create_checkpoint_signal(payload: CheckpointSignalCreateUpdate):
    conn = None
    try:
        new_id = str(uuid.uuid4())
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO checkpoint_signals
            (id, checkpoint_id, signal_id)
            VALUES (%s, %s, %s)
            """,
            (new_id, payload.checkpoint_id, payload.signal_id),
        )
        conn.commit()
        return admin_mutation(
            "created",
            new_id,
            checkpoint_id=payload.checkpoint_id,
            signal_id=payload.signal_id,
        )
    finally:
        if conn:
            conn.close()


@router.delete("/ui/checkpoint_signals/{checkpoint_signal_id}")
def delete_checkpoint_signal(checkpoint_signal_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM checkpoint_signals WHERE id = %s", (checkpoint_signal_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Checkpoint-signal link not found.")
        conn.commit()
        return admin_mutation("deleted", checkpoint_signal_id)
    finally:
        if conn:
            conn.close()


@router.get("/ui/checkpoint_signals")
def list_checkpoint_signals(
    page: int = 1,
    size: int = 10,
    tenant_id: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
    signal_id: Optional[str] = None,
):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        base_query = """
            SELECT cs.id, cs.checkpoint_id, cs.signal_id,
                   c.name as checkpoint_name, s.name as signal_name
              FROM checkpoint_signals cs
              JOIN checkpoints c ON cs.checkpoint_id = c.id
              JOIN signals s ON cs.signal_id = s.id
        """
        where_parts = []
        params: list = []
        if tenant_id:
            where_parts.append("c.tenant_id = %s")
            params.append(tenant_id)
        if checkpoint_id:
            where_parts.append("cs.checkpoint_id = %s")
            params.append(checkpoint_id)
        if signal_id:
            where_parts.append("cs.signal_id = %s")
            params.append(signal_id)
        if where_parts:
            base_query += " WHERE " + " AND ".join(where_parts)
        total, rows = paginate_query(cur, base_query, tuple(params), page, size)
        items = []
        for r in rows:
            items.append(
                {
                    "id": str(r[0]),
                    "checkpoint_id": str(r[1]),
                    "signal_id": str(r[2]),
                    "checkpoint_name": r[3],
                    "signal_name": r[4],
                }
            )
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@router.get("/ui/search_tenants")
def search_tenants(q: str, page: int = 1, size: int = 10):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        like = f"%{q}%"
        base_query = """
            SELECT id, name
              FROM tenants
             WHERE name ILIKE %s
                OR id::text ILIKE %s
        """
        params = (like, like)
        total, rows = paginate_query(cur, base_query, params, page, size)
        items = [{"id": str(r[0]), "name": r[1]} for r in rows]
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@router.get("/ui/search_checkpoints")
def search_checkpoints(
    q: str,
    tenant_id: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
):
    """
    Searches checkpoints by partial match in name, id::text, type, description,
    dsl_expression, or method_of_call.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        like = f"%{q}%"
        base_query = """
            SELECT c.id, c.tenant_id, c.name, c.description, c.type, c.dsl_expression,
                   CASE WHEN cv.checkpoint_id IS NOT NULL THEN true ELSE false END as is_current_version
              FROM checkpoints c
              LEFT JOIN checkpoint_current_version cv ON cv.checkpoint_id = c.id
             WHERE (c.name ILIKE %s
                OR c.id::text ILIKE %s
                OR c.type ILIKE %s
                OR c.description ILIKE %s
                OR c.dsl_expression ILIKE %s
                OR c.method_of_call ILIKE %s)
        """
        params = [like, like, like, like, like, like]

        if tenant_id:
            base_query += " AND c.tenant_id = %s"
            params.append(tenant_id)

        if active_only:
            base_query += " AND cv.checkpoint_id IS NOT NULL"

        base_query += " ORDER BY c.name ASC, c.id ASC"

        total, rows = paginate_query(cur, base_query, params, page, size)
        items = []
        for r in rows:
            items.append({
                "id": str(r[0]),
                "tenant_id": str(r[1]),
                "name": r[2],
                "description": r[3],
                "type": r[4],
                "dsl_expression": r[5],
                "is_current_version": r[6]
            })
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@router.get("/ui/search_signals")
def search_signals(q: str, tenant_id: Optional[str] = None, page: int = 1, size: int = 10, active_only: bool = False):
    """
    Searches signals by partial match in name, id::text, type, description,
    or method_of_call. Returns placeholders too.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        like = f"%{q}%"
        base_query = """
            SELECT s.id, s.tenant_id, s.name, s.description, s.type, s.method_of_call,
                   s.expression_body, s.cost, s.cache_expiration_seconds, s.timeout_seconds,
                   s.can_run_in_parallel, s.order_of_evaluation, s.http_method,
                   s.request_url_params_template, s.request_body_template,
                   s.request_headers_template, s.bearer_token, s.allow_caching,
                   s.global_reuse, s.function_params_template,
                   CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version
              FROM signals s
              LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
             WHERE (s.name ILIKE %s
                OR s.id::text ILIKE %s
                OR s.type ILIKE %s
                OR s.description ILIKE %s
                OR s.method_of_call ILIKE %s)
        """
        params = [like, like, like, like, like]
        
        if tenant_id:
            base_query += " AND s.tenant_id = %s"
            params.append(tenant_id)
        
        if active_only:
            base_query += " AND scv.signal_id IS NOT NULL"

        base_query += " ORDER BY s.name ASC, s.id ASC"

        total, rows = paginate_query(cur, base_query, params, page, size)
        items = [_admin_signal_item_from_row(r, include_current=True) for r in rows]
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@router.get("/ui/search_decisions")
def search_decisions(
    q: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    tenant_id: Optional[str] = None,
    page: int = 1,
    size: int = 10
):
    """
    Searches decisions by partial match in final_decision_value, correlation_id,
    applicant_id, checkpoint name, checkpoint_id::text, or in signal_log.signal_value.
    Also optional date filters.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        base_query = """
            SELECT dl.id, dl.checkpoint_id, dl.tenant_id, dl.applicant_id,
                   dl.final_decision_value, dl.cost_incurred, dl.correlation_id,
                   dl.decision_timestamp, c.name AS checkpoint_name
              FROM decision_log dl
         LEFT JOIN checkpoints c ON c.id = dl.checkpoint_id
         LEFT JOIN signal_log sl ON dl.id = sl.decision_log_id
             WHERE 1=1
        """
        conditions = []
        params = []

        if q:
            like = f"%{q}%"
            conditions.append(
                """
                (
                  dl.final_decision_value ILIKE %s
                  OR dl.correlation_id ILIKE %s
                  OR dl.applicant_id ILIKE %s
                  OR dl.checkpoint_id::text ILIKE %s
                  OR c.name ILIKE %s
                  OR sl.signal_value ILIKE %s
                )
                """
            )
            params.extend([like, like, like, like, like, like])

        if from_date:
            conditions.append("dl.decision_timestamp >= %s")
            params.append(from_date)
        if to_date:
            conditions.append("dl.decision_timestamp <= %s")
            params.append(to_date)

        if tenant_id:
            conditions.append("dl.tenant_id = %s")
            params.append(tenant_id)

        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        base_query += " GROUP BY dl.id, c.name"

        total, rows = paginate_query(cur, base_query, params, page, size)
        items = []
        for r in rows:
            items.append(
                {
                    "id": str(r[0]),
                    "checkpoint_id": str(r[1]),
                    "tenant_id": str(r[2]),
                    "applicant_id": r[3],
                    "final_decision_value": r[4],
                    "cost_incurred": r[5],
                    "correlation_id": r[6],
                    "decision_timestamp": r[7].isoformat() if r[7] else None,
                    "checkpoint_name": r[8],
                }
            )
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@router.get("/ui/search_signal_logs")
def search_signal_logs(
    q: Optional[str] = None,
    tenant_id: Optional[str] = None,
    failures_only: bool = False,
    page: int = 1,
    size: int = 10,
):
    """
    Searches signal_log by partial match in signal_id, applicant_id,
    decision_log_id, signal_value, cost_incurred, success, or id.
    Also includes param_values from signal_log_values.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Step 1: count how many overall signal_log rows match
        base_count_query = """
            SELECT COUNT(DISTINCT sl.id)
              FROM signal_log sl
         LEFT JOIN signals sig ON sig.id = sl.signal_id
         LEFT JOIN decision_log dl ON dl.id = sl.decision_log_id
             WHERE 1=1
        """
        count_conditions = []
        count_params = []

        if q:
            like = f"%{q}%"
            count_conditions.append(
                """
                (
                  sl.signal_id::text ILIKE %s
                  OR sl.applicant_id ILIKE %s
                  OR sl.decision_log_id::text ILIKE %s
                  OR sl.signal_value ILIKE %s
                  OR CAST(sl.cost_incurred AS text) ILIKE %s
                  OR CAST(sl.success AS text) ILIKE %s
                  OR sl.id::text ILIKE %s
                  OR sig.name ILIKE %s
                )
                """
            )
            count_params.extend([like, like, like, like, like, like, like, like])

        if tenant_id:
            count_conditions.append("dl.tenant_id = %s")
            count_params.append(tenant_id)

        if failures_only:
            count_conditions.append("sl.success = false")

        if count_conditions:
            base_count_query += " AND " + " AND ".join(count_conditions)

        cur.execute(base_count_query, count_params)
        total = cur.fetchone()[0]

        # Step 2: fetch actual rows (with left join to signal_log_values)
        base_data_query = """
            SELECT sl.id,
                   sl.decision_log_id,
                   sl.signal_id,
                   sl.applicant_id,
                   sl.signal_value,
                   sl.started_at,
                   sl.completed_at,
                   sl.cost_incurred,
                   sl.success,
                   slv.param_name,
                   slv.param_value,
                   sig.name AS signal_name
              FROM signal_log sl
         LEFT JOIN signals sig ON sig.id = sl.signal_id
         LEFT JOIN decision_log dl ON dl.id = sl.decision_log_id
         LEFT JOIN signal_log_values slv
                ON sl.id = slv.signal_log_id
             WHERE 1=1
        """
        data_conditions = []
        data_params = []

        if q:
            like = f"%{q}%"
            data_conditions.append(
                """
                (
                  sl.signal_id::text ILIKE %s
                  OR sl.applicant_id ILIKE %s
                  OR sl.decision_log_id::text ILIKE %s
                  OR sl.signal_value ILIKE %s
                  OR CAST(sl.cost_incurred AS text) ILIKE %s
                  OR CAST(sl.success AS text) ILIKE %s
                  OR sl.id::text ILIKE %s
                  OR slv.param_name ILIKE %s
                  OR slv.param_value ILIKE %s
                  OR sig.name ILIKE %s
                )
                """
            )
            data_params.extend([like, like, like, like, like, like, like, like, like, like])

        if tenant_id:
            data_conditions.append("dl.tenant_id = %s")
            data_params.append(tenant_id)

        if failures_only:
            data_conditions.append("sl.success = false")

        if data_conditions:
            base_data_query += " AND " + " AND ".join(data_conditions)

        base_data_query += " ORDER BY sl.started_at DESC"

        cur.execute(base_data_query, data_params)
        joined_rows = cur.fetchall()

        from collections import defaultdict
        log_map = defaultdict(lambda: {
            "id": None,
            "decision_log_id": None,
            "signal_id": None,
            "signal_name": None,
            "applicant_id": None,
            "signal_value": None,
            "started_at": None,
            "completed_at": None,
            "cost_incurred": None,
            "success": None,
            "param_values": []
        })

        for row in joined_rows:
            sl_id = str(row[0])
            if log_map[sl_id]["id"] is None:
                log_map[sl_id]["id"] = sl_id
                log_map[sl_id]["decision_log_id"] = str(row[1])
                log_map[sl_id]["signal_id"] = str(row[2])
                log_map[sl_id]["applicant_id"] = row[3]
                log_map[sl_id]["signal_value"] = row[4]
                log_map[sl_id]["started_at"] = row[5].isoformat() if row[5] else None
                log_map[sl_id]["completed_at"] = row[6].isoformat() if row[6] else None
                log_map[sl_id]["cost_incurred"] = row[7]
                log_map[sl_id]["success"] = row[8]
                log_map[sl_id]["signal_name"] = row[11]

            param_name = row[9]
            param_val = row[10]
            if param_name is not None:
                log_map[sl_id]["param_values"].append({
                    "param_name": param_name,
                    "param_value": param_val
                })

        all_logs = list(log_map.values())
        for log in all_logs:
            raw_map = {
                item["param_name"]: item["param_value"]
                for item in log["param_values"]
                if item.get("param_name") is not None
            }
            redacted_map = redact_param_map_for_response(raw_map)
            log["param_values"] = [
                {"param_name": name, "param_value": value}
                for name, value in redacted_map.items()
            ]

        # Apply pagination in memory
        start_index = (page - 1) * size
        end_index = start_index + size
        paginated_logs = all_logs[start_index:end_index]

        return {
            "items": paginated_logs,
            "total": total,
            "page": page,
            "size": size
        }

    finally:
        if conn:
            conn.close()


@router.get("/ui/promotion_audit")
def search_promotion_audit(
    tenant_id: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    size: int = 10,
):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        base_query = """
            SELECT id, tenant_id, resource_type, resource_id, resource_name,
                   actor_id, promotion_reason, source, created_at
              FROM promotion_audit
             WHERE 1=1
        """
        params: list[object] = []
        if tenant_id:
            base_query += " AND tenant_id = %s"
            params.append(tenant_id)
        if q:
            like = f"%{q}%"
            base_query += """
                AND (
                    resource_name ILIKE %s
                    OR promotion_reason ILIKE %s
                    OR actor_id ILIKE %s
                    OR resource_type ILIKE %s
                )
            """
            params.extend([like, like, like, like])
        base_query += " ORDER BY created_at DESC, id ASC"

        total, rows = paginate_query(cur, base_query, params, page, size)
        items = [_promotion_audit_row_to_item(row) for row in rows]
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


def _promotion_audit_row_to_item(row) -> dict:
    return {
        "id": str(row[0]),
        "tenant_id": str(row[1]),
        "resource_type": row[2],
        "resource_id": str(row[3]),
        "resource_name": row[4],
        "actor_id": row[5],
        "promotion_reason": row[6],
        "source": row[7],
        "created_at": row[8].isoformat() if row[8] else None,
    }


@router.get("/ui/promotion_audit/{promotion_id}")
def get_promotion_audit(promotion_id: UuidStr, tenant_id: Optional[str] = None):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, tenant_id, resource_type, resource_id, resource_name,
                   actor_id, promotion_reason, source, created_at
              FROM promotion_audit
             WHERE id = %s
            """,
            (promotion_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Promotion audit record not found.")
        if tenant_id and str(row[1]) != tenant_id:
            raise HTTPException(status_code=404, detail="Promotion audit record not found.")
        return _promotion_audit_row_to_item(row)
    finally:
        if conn:
            conn.close()


@router.post("/ui/dsl_preflight")
def dsl_preflight(payload: DslPreflightRequest):
    """Validate DSL syntax using the same policy as runtime evaluation."""
    known_names = list(payload.signal_names) + list(payload.known_names)
    return preflight_dsl(
        payload.dsl_expression,
        known_names,
        binding_mode=payload.binding_mode,
        expression_kind=payload.expression_kind,
    )


@router.post("/ui/checkpoints/{checkpoint_id}/make_current")
def make_checkpoint_current(
    checkpoint_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_admin),
):
    """Make a checkpoint the current version for its tenant and name."""
    promotion_reason = normalize_promotion_reason(payload.promotion_reason)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # First get the checkpoint details
        cur.execute("""
            SELECT tenant_id, name, dsl_expression
            FROM checkpoints
            WHERE id = %s
        """, (checkpoint_id,))
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        
        tenant_id, checkpoint_name, dsl_expression = result

        cur.execute(
            """
            SELECT s.name
              FROM checkpoint_signals cs
              JOIN signals s ON s.id = cs.signal_id
             WHERE cs.checkpoint_id = %s
            """,
            (checkpoint_id,),
        )
        signal_names = [row[0] for row in cur.fetchall()]
        dsl_result = validate_expression(dsl_expression, signal_names, "strict")
        if not dsl_result.ok:
            raise HTTPException(status_code=422, detail="; ".join(dsl_result.errors))

        # Update or insert into checkpoint_current_version
        cur.execute("""
            INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, name) 
            DO UPDATE SET 
                checkpoint_id = EXCLUDED.checkpoint_id,
                updated_at = NOW()
        """, (tenant_id, checkpoint_name, checkpoint_id))

        record_promotion_audit(
            cur,
            tenant_id=str(tenant_id),
            resource_type="checkpoint",
            resource_id=checkpoint_id,
            resource_name=checkpoint_name,
            actor_id=auth.actor_id,
            promotion_reason=promotion_reason,
        )
        
        conn.commit()
        return admin_mutation("promoted", checkpoint_id)
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="make_checkpoint_current failed")
    finally:
        cur.close()
        conn.close()


@router.post("/ui/signals/{signal_id}/make_current")
def make_signal_current(
    signal_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_admin),
):
    """Set a signal as the current version for its tenant and name."""
    promotion_reason = normalize_promotion_reason(payload.promotion_reason)
    conn = get_db_connection()
    try:
        # Get the tenant_id and name for this signal
        cur = conn.cursor()
        cur.execute(
            "SELECT tenant_id, name FROM signals WHERE id = %s",
            (signal_id,)
        )
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        tenant_id, signal_name = result

        # Update or insert into signal_current_version
        cur.execute("""
            INSERT INTO signal_current_version (tenant_id, name, signal_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET signal_id = EXCLUDED.signal_id,
                updated_at = NOW()
        """, (tenant_id, signal_name, signal_id))

        record_promotion_audit(
            cur,
            tenant_id=str(tenant_id),
            resource_type="signal",
            resource_id=signal_id,
            resource_name=signal_name,
            actor_id=auth.actor_id,
            promotion_reason=promotion_reason,
        )
        
        conn.commit()
        return admin_mutation("promoted", signal_id)
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="make_signal_current failed")
    finally:
        conn.close()
