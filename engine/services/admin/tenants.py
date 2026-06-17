"""Tenant CRUD for admin UI."""

from fastapi import HTTPException

from ...auth import AuthContext, assert_admin_tenant_access, resolve_admin_tenant_id
from ...db import get_db_connection
from ...models import TenantCreateUpdate
from ...services.admin_responses import admin_mutation
from ...services.pagination import (
    MAX_PAGE_SIZE,
    build_paginated_response,
    paginate_query,
)
from ...types import UuidStr
from .common import collect_all_pages, raise_admin_error


def create_tenant(payload: TenantCreateUpdate, *, auth: AuthContext) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if payload.copy_from_tenant_id:
            assert_admin_tenant_access(auth, payload.copy_from_tenant_id)

        cur.execute(
            "INSERT INTO tenants (name) VALUES (%s) RETURNING id",
            (payload.name,),
        )
        new_tenant_id = cur.fetchone()[0]

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


def list_tenants(*, auth: AuthContext, page: int = 1, size: int = 10) -> dict:
    scope_tenant_id = resolve_admin_tenant_id(auth, None, required=False)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if scope_tenant_id:
            base_query = (
                "SELECT id, name FROM tenants WHERE id = %s ORDER BY name ASC, id ASC"
            )
            params: tuple = (scope_tenant_id,)
        else:
            base_query = "SELECT id, name FROM tenants ORDER BY name ASC, id ASC"
            params = ()
        total, rows, page, size = paginate_query(cur, base_query, params, page, size)
        items = [{"id": str(r[0]), "name": r[1]} for r in rows]
        return build_paginated_response(items, total, page, size)
    finally:
        conn.close()


def list_all_tenants(*, auth: AuthContext) -> list:
    return collect_all_pages(
        lambda page: list_tenants(auth=auth, page=page, size=MAX_PAGE_SIZE)
    )


def get_tenant(tenant_id: UuidStr, *, auth: AuthContext) -> dict:
    assert_admin_tenant_access(auth, tenant_id)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM tenants WHERE id=%s", (tenant_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        return {"id": str(row[0]), "name": row[1]}
    finally:
        conn.close()


def update_tenant(tenant_id: UuidStr, payload: TenantCreateUpdate, *, auth: AuthContext) -> dict:
    assert_admin_tenant_access(auth, tenant_id)
    conn = get_db_connection()
    try:
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
        conn.close()


def delete_tenant(tenant_id: UuidStr, *, auth: AuthContext) -> dict:
    assert_admin_tenant_access(auth, tenant_id)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        conn.commit()
        return admin_mutation("deleted", tenant_id)
    finally:
        conn.close()
