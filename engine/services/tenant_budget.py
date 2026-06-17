"""Tenant period budget ledger with atomic pre-vendor leases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from ..db import db_cursor


@dataclass
class TenantBudgetState:
    limit_units: int
    used_units: int
    reserved_units: int
    window_days: int
    window_mode: str
    window_anchor: datetime

    @property
    def remaining_units(self) -> int:
        return max(0, self.limit_units - self.used_units - self.reserved_units)


def _rollover_if_needed(cur, tenant_id: str, row) -> tuple:
    limit_units, used_units, reserved_units, window_days, window_mode, window_anchor = row
    now = datetime.utcnow()
    if window_mode == "rolling":
        anchor = window_anchor
        if now >= anchor + timedelta(days=window_days):
            used_units = 0
            reserved_units = 0
            anchor = now
            cur.execute(
                """
                UPDATE tenant_budgets
                   SET used_units = 0,
                       reserved_units = 0,
                       window_anchor = %s,
                       updated_at = NOW()
                 WHERE tenant_id = %s
                """,
                (anchor, tenant_id),
            )
        return limit_units, used_units, reserved_units, window_days, window_mode, anchor
    anchor = window_anchor
    period_end = anchor + timedelta(days=window_days)
    while now >= period_end:
        anchor = period_end
        period_end = anchor + timedelta(days=window_days)
    if anchor != window_anchor:
        used_units = 0
        reserved_units = 0
        cur.execute(
            """
            UPDATE tenant_budgets
               SET used_units = 0,
                   reserved_units = 0,
                   window_anchor = %s,
                   updated_at = NOW()
             WHERE tenant_id = %s
            """,
            (anchor, tenant_id),
        )
    return limit_units, used_units, reserved_units, window_days, window_mode, anchor


def load_tenant_budget(tenant_id: str) -> Optional[TenantBudgetState]:
    with db_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT limit_units, used_units, reserved_units, window_days, window_mode, window_anchor
              FROM tenant_budgets
             WHERE tenant_id = %s
            """,
            (tenant_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        limit_units, used_units, reserved_units, window_days, window_mode, window_anchor = (
            _rollover_if_needed(cur, tenant_id, row)
        )
        conn.commit()
        return TenantBudgetState(
            limit_units=limit_units,
            used_units=used_units,
            reserved_units=reserved_units,
            window_days=window_days,
            window_mode=window_mode,
            window_anchor=window_anchor,
        )


def tenant_budget_remaining_units(tenant_id: str) -> Optional[int]:
    budget = load_tenant_budget(tenant_id)
    return budget.remaining_units if budget else None


def lease_tenant_budget_units(tenant_id: str, units: int) -> bool:
    """Atomically reserve tenant budget before a vendor call. Commits immediately."""
    if units <= 0:
        return True
    with db_cursor() as (conn, cur):
        cur.execute(
            "SELECT limit_units, used_units, reserved_units, window_days, window_mode, window_anchor "
            "FROM tenant_budgets WHERE tenant_id = %s",
            (tenant_id,),
        )
        row = cur.fetchone()
        if not row:
            return True
        limit_units, used_units, reserved_units, window_days, window_mode, window_anchor = (
            _rollover_if_needed(cur, tenant_id, row)
        )
        cur.execute(
            """
            UPDATE tenant_budgets
               SET reserved_units = reserved_units + %s,
                   updated_at = NOW()
             WHERE tenant_id = %s
               AND used_units + reserved_units + %s <= limit_units
            RETURNING 1
            """,
            (units, tenant_id, units),
        )
        ok = cur.fetchone() is not None
        conn.commit()
        return ok


def finalize_tenant_budget_signal(tenant_id: str, leased_units: int, actual_units: int) -> None:
    """Convert a pre-vendor lease to actual spend (or release unused lease headroom)."""
    if leased_units <= 0:
        return
    actual_units = max(0, actual_units)
    with db_cursor() as (conn, cur):
        cur.execute(
            """
            UPDATE tenant_budgets
               SET reserved_units = GREATEST(0, reserved_units - %s),
                   used_units = used_units + %s,
                   updated_at = NOW()
             WHERE tenant_id = %s
            """,
            (leased_units, actual_units, tenant_id),
        )
        conn.commit()


def release_tenant_budget_lease(tenant_id: str, units: int) -> None:
    """Release a lease when no vendor spend occurred."""
    if units <= 0:
        return
    with db_cursor() as (conn, cur):
        cur.execute(
            """
            UPDATE tenant_budgets
               SET reserved_units = GREATEST(0, reserved_units - %s),
                   updated_at = NOW()
             WHERE tenant_id = %s
            """,
            (units, tenant_id),
        )
        conn.commit()


def apply_tenant_budget_usage(
    cur, tenant_id: str, actual_units: int, *, force: bool = False
) -> bool:
    """Bulk increment for override path when per-signal leases were skipped."""
    if actual_units <= 0:
        return True
    cur.execute(
        "SELECT 1 FROM tenant_budgets WHERE tenant_id = %s",
        (tenant_id,),
    )
    if cur.fetchone() is None:
        return True
    if force:
        cur.execute(
            """
            UPDATE tenant_budgets
               SET used_units = used_units + %s,
                   updated_at = NOW()
             WHERE tenant_id = %s
            """,
            (actual_units, tenant_id),
        )
        return cur.rowcount > 0
    cur.execute(
        """
        UPDATE tenant_budgets
           SET used_units = used_units + %s,
               updated_at = NOW()
         WHERE tenant_id = %s
           AND used_units + reserved_units + %s <= limit_units
        RETURNING used_units
        """,
        (actual_units, tenant_id, actual_units),
    )
    return cur.fetchone() is not None


def normalize_override_reason(reason: str | None) -> str:
    if reason is None:
        raise ValueError("overrideReason is required when budgetOverride is true.")
    trimmed = reason.strip()
    if len(trimmed) < 3:
        raise ValueError("overrideReason must be at least 3 characters.")
    if len(trimmed) > 2000:
        raise ValueError("overrideReason must be at most 2000 characters.")
    return trimmed
