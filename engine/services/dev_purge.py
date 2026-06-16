"""Dev-only tenant data purge helpers (audit/log/cache rows).

Guarded by DECISION_ENGINE_DEV_PURGE and a separate confirm token header.
Never enable in production deployments.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException

from ..config import logger

DEV_PURGE_BODY_PHRASE = (
    "I understand this permanently deletes dev audit data for the tenant"
)

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def dev_purge_enabled() -> bool:
    return os.environ.get("DECISION_ENGINE_DEV_PURGE", "").strip().lower() in _TRUE_VALUES


def dev_purge_confirm_token() -> str | None:
    token = os.environ.get("DECISION_ENGINE_DEV_PURGE_CONFIRM", "").strip()
    return token or None


def assert_dev_purge_enabled() -> None:
    if not dev_purge_enabled():
        raise HTTPException(status_code=404, detail="Not found.")


def assert_dev_purge_confirm_configured() -> None:
    """Refuse purge when enabled without a server-side confirm token (fail closed)."""
    if dev_purge_enabled() and not dev_purge_confirm_token():
        raise HTTPException(
            status_code=500,
            detail=(
                "DECISION_ENGINE_DEV_PURGE is enabled but DECISION_ENGINE_DEV_PURGE_CONFIRM "
                "is not set. Refusing dev purge."
            ),
        )


def assert_dev_purge_confirm_header(header_value: str | None) -> None:
    assert_dev_purge_confirm_configured()
    expected = dev_purge_confirm_token()
    if not header_value or header_value != expected:
        raise HTTPException(
            status_code=403,
            detail="Missing or invalid X-Dev-Purge-Confirm header for dev purge.",
        )


def assert_dev_purge_body(*, confirm_phrase: str, purge_reason: str) -> None:
    if confirm_phrase != DEV_PURGE_BODY_PHRASE:
        raise HTTPException(
            status_code=422,
            detail="confirmPhrase does not match the required dev purge acknowledgement.",
        )
    if len(purge_reason.strip()) < 10:
        raise HTTPException(status_code=422, detail="purgeReason is too short.")


def purge_tenant_operational_data(cur, tenant_id: str) -> dict[str, int]:
    """Delete audit/log/cache/promotion rows for a tenant. Does not delete config rows."""
    cur.execute("SELECT id FROM tenants WHERE id = %s", (tenant_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Tenant not found.")

    deleted: dict[str, int] = {}

    cur.execute(
        """
        DELETE FROM signal_log_values slv
         USING signal_log sl
          JOIN decision_log dl ON dl.id = sl.decision_log_id
         WHERE slv.signal_log_id = sl.id
           AND dl.tenant_id = %s
        """,
        (tenant_id,),
    )
    deleted["signal_log_values"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM signal_log sl
         USING decision_log dl
         WHERE sl.decision_log_id = dl.id
           AND dl.tenant_id = %s
        """,
        (tenant_id,),
    )
    deleted["signal_log"] = cur.rowcount

    cur.execute("DELETE FROM decision_log WHERE tenant_id = %s", (tenant_id,))
    deleted["decision_log"] = cur.rowcount

    cur.execute("DELETE FROM signal_cached_values WHERE tenant_id = %s", (tenant_id,))
    deleted["signal_cached_values"] = cur.rowcount

    cur.execute("DELETE FROM promotion_audit WHERE tenant_id = %s", (tenant_id,))
    deleted["promotion_audit"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM signal_variable_values svv
         USING signals s
         WHERE svv.signal_id = s.id
           AND s.tenant_id = %s
        """,
        (tenant_id,),
    )
    deleted["signal_variable_values"] = cur.rowcount

    return deleted


def log_dev_purge(actor_id: str, tenant_id: str, purge_reason: str, deleted: dict[str, Any]) -> None:
    logger.warning(
        "DEV PURGE tenant_id=%s actor_id=%s reason=%r deleted=%s",
        tenant_id,
        actor_id,
        purge_reason,
        deleted,
    )
