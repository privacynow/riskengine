"""Signal CRUD and listing for admin UI."""

from fastapi import HTTPException

from ...auth import AuthContext, assert_admin_tenant_access
from ...db import get_db_connection
from ...models import SignalCreateUpdate, SignalMetadataUpdate
from ...services.admin_responses import admin_mutation
from ...services.dsl import validate_expression
from ...services.pagination import (
    MAX_PAGE_SIZE,
    build_paginated_response,
    clamp_pagination,
    paginate_query,
)
from ...services.resource_lifecycle import assert_not_current_signal
from ...services.signal_types import normalize_signal_type
from ...types import OptionalUuidStr, UuidStr
from .common import (
    admin_signal_item_from_row,
    assert_checkpoint_tenant,
    collect_all_pages,
    raise_admin_error,
    resolve_signal_bearer_token,
    validate_signal_templates,
)


def create_signal(payload: SignalCreateUpdate) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        validate_signal_templates(payload)
        signal_type = normalize_signal_type(payload.type)
        if signal_type == "expression" and payload.expression_body:
            result = validate_expression(
                payload.expression_body,
                [],
                "warn_unknown",
            )
            if not result.ok:
                raise HTTPException(status_code=422, detail="; ".join(result.errors))
        bearer_token = resolve_signal_bearer_token(cur, payload)
        cur.execute(
            """
            INSERT INTO signals (
                tenant_id, name, description, type, method_of_call,
                expression_body, cost, cache_expiration_seconds, timeout_seconds,
                can_run_in_parallel, order_of_evaluation, http_method,
                request_url_params_template, request_body_template,
                request_headers_template, bearer_token, allow_caching,
                global_reuse, function_params_template,
                default_priority, billable_event, cache_scope,
                vendor_name, vendor_product, is_expensive_vendor
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                payload.tenant_id,
                payload.name,
                payload.description,
                signal_type,
                payload.method_of_call,
                payload.expression_body,
                payload.cost,
                payload.cache_expiration_seconds,
                payload.timeout_seconds,
                payload.can_run_in_parallel,
                payload.order_of_evaluation,
                payload.http_method,
                payload.request_url_params_template,
                payload.request_body_template,
                payload.request_headers_template,
                bearer_token,
                payload.allow_caching,
                payload.global_reuse,
                payload.function_params_template,
                payload.default_priority,
                payload.billable_event,
                payload.cache_scope,
                payload.vendor_name,
                payload.vendor_product,
                payload.is_expensive_vendor,
            ),
        )

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

        conn.commit()
        return admin_mutation("created", new_signal_id)

    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="create_signal failed")
    finally:
        cur.close()
        conn.close()


def list_signals(
    *,
    checkpoint_id: OptionalUuidStr = None,
    scoped_tenant_id: OptionalUuidStr = None,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
) -> dict:
    page, size = clamp_pagination(page, size)
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if checkpoint_id and scoped_tenant_id:
            assert_checkpoint_tenant(cur, checkpoint_id, scoped_tenant_id)

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
                       CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version,
                       EXISTS (
                           SELECT 1
                             FROM signal_current_version scvn
                            WHERE scvn.tenant_id = s.tenant_id
                              AND scvn.name = s.name
                       ) as name_has_current_version
                  FROM signals s
                  JOIN checkpoint_signals cs ON cs.signal_id = s.id
                  LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
                 WHERE cs.checkpoint_id = %s
            """
            params = [checkpoint_id]
            if active_only:
                base_query += " AND scv.signal_id IS NOT NULL"
        elif scoped_tenant_id:
            base_query = """
                SELECT s.id, s.tenant_id, s.name, s.description, s.type,
                       s.method_of_call, s.expression_body, s.cost,
                       s.cache_expiration_seconds, s.timeout_seconds,
                       s.can_run_in_parallel, s.order_of_evaluation,
                       s.http_method, s.request_url_params_template,
                       s.request_body_template, s.request_headers_template,
                       s.bearer_token, s.allow_caching, s.global_reuse,
                       s.function_params_template,
                       CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version,
                       EXISTS (
                           SELECT 1
                             FROM signal_current_version scvn
                            WHERE scvn.tenant_id = s.tenant_id
                              AND scvn.name = s.name
                       ) as name_has_current_version
                  FROM signals s
                  LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
                 WHERE s.tenant_id = %s
            """
            params = [scoped_tenant_id]
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
                       CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version,
                       EXISTS (
                           SELECT 1
                             FROM signal_current_version scvn
                            WHERE scvn.tenant_id = s.tenant_id
                              AND scvn.name = s.name
                       ) as name_has_current_version
                  FROM signals s
                  LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
            """
            params = []
            if active_only:
                base_query += " WHERE scv.signal_id IS NOT NULL"

        base_query += " ORDER BY s.name ASC, s.id ASC"

        total, rows, page, size = paginate_query(cur, base_query, params, page, size)
        items = [admin_signal_item_from_row(r, include_current=True) for r in rows]

        return build_paginated_response(items, total, page, size)
    finally:
        conn.close()


def list_all_signals(
    *,
    scoped_tenant_id: OptionalUuidStr = None,
    checkpoint_id: OptionalUuidStr = None,
    active_only: bool = False,
) -> list:
    return collect_all_pages(
        lambda page: list_signals(
            checkpoint_id=checkpoint_id,
            scoped_tenant_id=scoped_tenant_id,
            page=page,
            size=MAX_PAGE_SIZE,
            active_only=active_only,
        )
    )


def get_signal(signal_id: UuidStr, *, auth: AuthContext) -> dict:
    conn = get_db_connection()
    try:
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
                   CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END AS is_current_version,
                   EXISTS (
                       SELECT 1
                         FROM signal_current_version scvn
                        WHERE scvn.tenant_id = s.tenant_id
                          AND scvn.name = s.name
                   ) AS name_has_current_version
              FROM signals s
              LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
             WHERE s.id = %s
            """,
            (signal_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Signal not found.")
        assert_admin_tenant_access(auth, str(row[1]))

        return admin_signal_item_from_row(row, include_current=True)
    finally:
        conn.close()


def update_signal(signal_id: UuidStr, payload: SignalMetadataUpdate) -> dict:
    conn = get_db_connection()
    try:
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
        conn.close()


def delete_signal(signal_id: UuidStr) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        assert_not_current_signal(cur, signal_id)
        cur.execute("DELETE FROM signals WHERE id = %s", (signal_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Signal not found.")
        conn.commit()
        return admin_mutation("deleted", signal_id)
    finally:
        conn.close()
