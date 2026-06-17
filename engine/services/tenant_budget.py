"""Tenant period budget ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from ..db import db_cursor


@dataclass
class TenantBudgetState:
    limit_units: int
    used_units: int
    window_days: int
    window_mode: str
    window_anchor: datetime

    @property
    def remaining_units(self) -> int:
        return max(0, self.limit_units - self.used_units)


def _rollover_if_needed(cur, tenant_id: str, row) -> tuple:
    limit_units, used_units, window_days, window_mode, window_anchor = row
    now = datetime.utcnow()
    if window_mode == "rolling":
        anchor = window_anchor
        if now >= anchor + timedelta(days=window_days):
            used_units = 0
            anchor = now
            cur.execute(
                """
                UPDATE tenant_budgets
                   SET used_units = 0,
                       window_anchor = %s,
                       updated_at = NOW()
                 WHERE tenant_id = %s
                """,
                (anchor, tenant_id),
            )
        return limit_units, used_units, window_days, window_mode, anchor
    # anchored periods from window_anchor
    anchor = window_anchor
    period_end = anchor + timedelta(days=window_days)
    while now >= period_end:
        anchor = period_end
        period_end = anchor + timedelta(days=window_days)
    if anchor != window_anchor or used_units and now < anchor + timedelta(days=window_days):
        if anchor != window_anchor:
            used_units = 0
            cur.execute(
                """
                UPDATE tenant_budgets
                   SET used_units = 0,
                       window_anchor = %s,
                       updated_at = NOW()
                 WHERE tenant_id = %s
                """,
                (anchor, tenant_id),
            )
    return limit_units, used_units, window_days, window_mode, anchor


def load_tenant_budget(tenant_id: str) -> Optional[TenantBudgetState]:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT limit_units, used_units, window_days, window_mode, window_anchor
              FROM tenant_budgets
             WHERE tenant_id = %s
            """,
            (tenant_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        limit_units, used_units, window_days, window_mode, window_anchor = _rollover_if_needed(
            cur, tenant_id, row
        )
        return TenantBudgetState(
            limit_units=limit_units,
            used_units=used_units,
            window_days=window_days,
            window_mode=window_mode,
            window_anchor=window_anchor,
        )


def reserve_tenant_budget(tenant_id: str, units: int, budget: TenantBudgetState) -> bool:
    if units <= 0:
        return True
    return budget.used_units + units <= budget.limit_units


def apply_tenant_budget_usage(cur, tenant_id: str, actual_units: int) -> None:
    if actual_units <= 0:
        return
    cur.execute(
        """
        UPDATE tenant_budgets
           SET used_units = used_units + %s,
               updated_at = NOW()
         WHERE tenant_id = %s
        """,
        (actual_units, tenant_id),
    )
