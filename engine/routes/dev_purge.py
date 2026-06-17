"""Dev-only destructive purge routes. Disabled unless DECISION_ENGINE_DEV_PURGE is set."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from ..auth import AuthContext, require_permission
from ..db import get_db_connection
from ..models import DevTenantPurgeRequest
from ..services.dev_purge import (
    DEV_PURGE_BODY_PHRASE,
    assert_dev_purge_body,
    assert_dev_purge_confirm_configured,
    assert_dev_purge_confirm_header,
    assert_dev_purge_enabled,
    log_dev_purge,
    purge_tenant_operational_data,
)

router = APIRouter(
    tags=["dev-purge"],
    dependencies=[Depends(require_permission("admin:write"))],
    include_in_schema=False,
)


def _require_dev_purge_gate(
    x_dev_purge_confirm: str | None = Header(default=None, alias="X-Dev-Purge-Confirm"),
) -> None:
    assert_dev_purge_enabled()
    assert_dev_purge_confirm_header(x_dev_purge_confirm)


@router.get("/ui/dev/purge/status")
def dev_purge_status():
    """Whether dev purge is enabled in this process."""
    assert_dev_purge_confirm_configured()
    return {
        "enabled": True,
        "requires_header": "X-Dev-Purge-Confirm",
        "requires_confirm_phrase": DEV_PURGE_BODY_PHRASE,
    }


@router.post("/ui/dev/purge/tenant")
def purge_tenant_dev_data(
    payload: DevTenantPurgeRequest,
    auth: AuthContext = Depends(require_permission("admin:write")),
    _: None = Depends(_require_dev_purge_gate),
):
    """
    Permanently delete dev audit/log/cache rows for one tenant.

    Guardrails (all required):
    - Server env `DECISION_ENGINE_DEV_PURGE=1`
    - Header `X-Dev-Purge-Confirm` matching `DECISION_ENGINE_DEV_PURGE_CONFIRM`
    - Body `confirmPhrase` exactly: "I understand this permanently deletes dev audit data for the tenant"
    - Body `purgeReason` (logged, min 10 chars)

    Does not delete checkpoints, signals, associations, or the tenant row.
    """
    assert_dev_purge_body(
        confirm_phrase=payload.confirm_phrase,
        purge_reason=payload.purge_reason,
    )
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        deleted = purge_tenant_operational_data(cur, payload.tenant_id)
        conn.commit()
        log_dev_purge(auth.actor_id, payload.tenant_id, payload.purge_reason, deleted)
        return {
            "action": "purged",
            "tenant_id": payload.tenant_id,
            "deleted": deleted,
        }
    finally:
        if conn:
            conn.close()
