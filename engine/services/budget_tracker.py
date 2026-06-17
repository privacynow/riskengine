"""In-decision checkpoint budget reservation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


@dataclass
class BudgetTracker:
    checkpoint_cap: Optional[int]
    tenant_limit: Optional[int]
    tenant_used: int
    budget_override: bool = False
    checkpoint_actual: int = 0
    checkpoint_reserved: int = 0
    checkpoint_total_reserved: int = 0
    tenant_reserved: int = 0
    tenant_actual_charged: int = 0

    @property
    def checkpoint_committed(self) -> int:
        return self.checkpoint_actual + self.checkpoint_reserved

    @property
    def tenant_committed(self) -> int:
        if self.tenant_limit is None:
            return 0
        return self.tenant_used + self.tenant_reserved

    @property
    def tenant_remaining_after_commit(self) -> Optional[int]:
        if self.tenant_limit is None:
            return None
        return max(0, self.tenant_limit - self.tenant_used - self.tenant_actual_charged)

    def try_reserve(self, units: int) -> bool:
        if self.budget_override or units <= 0:
            return True
        if self.checkpoint_cap is not None and self.checkpoint_committed + units > self.checkpoint_cap:
            return False
        if self.tenant_limit is not None and self.tenant_committed + units > self.tenant_limit:
            return False
        self.checkpoint_reserved += units
        self.checkpoint_total_reserved += units
        self.tenant_reserved += units
        return True

    def release_reserve(self, units: int) -> None:
        if units <= 0:
            return
        self.checkpoint_reserved = max(0, self.checkpoint_reserved - units)
        self.tenant_reserved = max(0, self.tenant_reserved - units)

    def commit_actual(self, *, reserved_units: int, actual_units: int) -> None:
        self.release_reserve(reserved_units)
        self.checkpoint_actual += actual_units


def admit_signals_under_budget(
    candidates: List[Any],
    tracker: BudgetTracker,
) -> Tuple[List[Any], List[Any]]:
    """Greedy admission in candidate order; reserves worst-case cost per admitted signal."""
    admitted: List[Any] = []
    rejected: List[Any] = []
    for sig in candidates:
        est = getattr(sig, "cost", 0)
        if tracker.try_reserve(est):
            admitted.append(sig)
        else:
            rejected.append(sig)
    return admitted, rejected
