"""Version history queries for signals and checkpoints."""

from fastapi import HTTPException

from ...auth import AuthContext, assert_admin_tenant_access
from ...db import get_db_connection
from ...types import UuidStr
from .common import admin_signal_item_from_row, checkpoint_item_from_row


def list_signal_versions(signal_id: UuidStr, *, auth: AuthContext) -> list[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT tenant_id, name FROM signals WHERE id = %s",
            (signal_id,),
        )
        anchor = cur.fetchone()
        if not anchor:
            raise HTTPException(status_code=404, detail="Signal not found.")
        tenant_id, name = anchor
        assert_admin_tenant_access(auth, str(tenant_id))

        cur.execute(
            """
            SELECT s.id, s.tenant_id, s.name, s.description, s.type,
                   s.method_of_call, s.expression_body, s.cost,
                   s.cache_expiration_seconds, s.timeout_seconds,
                   s.can_run_in_parallel, s.order_of_evaluation,
                   s.http_method, s.request_url_params_template,
                   s.request_body_template, s.request_headers_template,
                   s.bearer_token, s.allow_caching, s.global_reuse,
                   s.function_params_template,
                   CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END,
                   EXISTS (
                       SELECT 1
                         FROM signal_current_version scvn
                        WHERE scvn.tenant_id = s.tenant_id
                          AND scvn.name = s.name
                   ),
                   s.updated_at
              FROM signals s
              LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
             WHERE s.tenant_id = %s AND s.name = %s
             ORDER BY s.updated_at DESC, s.id DESC
            """,
            (tenant_id, name),
        )
        return [admin_signal_item_from_row(row, include_current=True) for row in cur.fetchall()]
    finally:
        conn.close()


def list_checkpoint_versions(checkpoint_id: UuidStr, *, auth: AuthContext) -> list[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT tenant_id, name FROM checkpoints WHERE id = %s",
            (checkpoint_id,),
        )
        anchor = cur.fetchone()
        if not anchor:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
        tenant_id, name = anchor
        assert_admin_tenant_access(auth, str(tenant_id))

        cur.execute(
            """
            SELECT c.id, c.tenant_id, c.name, c.description, c.type, c.dsl_expression,
                   c.method_of_call, c.max_cost, c.override_cost_flag,
                   c.budget_exceeded_policy, c.vendor_failure_policy,
                   c.terminal_decline_signal_names, c.timeout_seconds,
                   CASE WHEN cv.checkpoint_id IS NOT NULL THEN true ELSE false END,
                   EXISTS (
                       SELECT 1
                         FROM checkpoint_current_version cvn
                        WHERE cvn.tenant_id = c.tenant_id
                          AND cvn.name = c.name
                   ),
                   c.updated_at
              FROM checkpoints c
              LEFT JOIN checkpoint_current_version cv ON cv.checkpoint_id = c.id
             WHERE c.tenant_id = %s AND c.name = %s
             ORDER BY c.updated_at DESC, c.id DESC
            """,
            (tenant_id, name),
        )
        return [checkpoint_item_from_row(row) for row in cur.fetchall()]
    finally:
        conn.close()
