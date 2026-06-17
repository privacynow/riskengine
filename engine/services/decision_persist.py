"""Atomic persistence for completed decision outcomes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..audit import persist_signal_logs
from .promotion_audit import record_promotion_audit
from .tenant_budget import apply_tenant_budget_usage


def persist_decision_outcome(
    conn,
    cur,
    *,
    decision_id: str,
    checkpoint_id: str,
    tenant_id: str,
    applicant_id: str | None,
    correlation_id: str | None,
    decision_timestamp: datetime,
    decision_outcome: str,
    decision_reason: str,
    degraded: bool,
    estimated_cost_units: int,
    reserved_cost_units: int,
    actual_cost_units: int,
    budget_units: int | None,
    pending_signal_logs: list[dict[str, Any]],
    pending_db_cache_writes: list[dict[str, Any]],
    tenant_budget_apply_units: int = 0,
    budget_override_audit: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Write decision_log, signal audit rows, cache rows, and tenant budget in one transaction."""
    outcome = decision_outcome
    reason = decision_reason

    if tenant_budget_apply_units > 0:
        force_tenant = budget_override_audit is not None
        if not apply_tenant_budget_usage(
            cur, tenant_id, tenant_budget_apply_units, force=force_tenant
        ):
            outcome = "REFER"
            reason = "tenant_budget_exceeded_at_persist"

    cur.execute(
        """
        INSERT INTO decision_log
        (id, checkpoint_id, tenant_id, applicant_id,
         final_decision_value, decision_outcome, decision_reason, degraded,
         cost_incurred, estimated_cost_units, reserved_cost_units, actual_cost_units,
         budget_units, correlation_id, decision_timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            decision_id,
            checkpoint_id,
            tenant_id,
            applicant_id,
            outcome,
            outcome,
            reason,
            degraded,
            actual_cost_units,
            estimated_cost_units,
            reserved_cost_units,
            actual_cost_units,
            budget_units,
            correlation_id,
            decision_timestamp,
        ),
    )
    persist_signal_logs(cur, pending_signal_logs)
    for cache_item in pending_db_cache_writes:
        checkpoint_id_for_cache = cache_item.get("checkpoint_id")
        cur.execute(
            """
            INSERT INTO signal_cached_values
            (id, tenant_id, checkpoint_id, signal_id, applicant_id, signal_value, expires_at)
            VALUES (uuid_generate_v4(), %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                cache_item["tenant_id"],
                checkpoint_id_for_cache,
                cache_item["signal_id"],
                cache_item["applicant_key"],
                cache_item["value_str"],
                cache_item["expires_at"],
            ),
        )
        if cache_item.get("cache_scope") == "tenant_checkpoint_applicant":
            cur.execute(
                """
                UPDATE signal_cached_values
                   SET signal_value = %s,
                       expires_at = %s,
                       updated_at = NOW()
                 WHERE tenant_id = %s
                   AND checkpoint_id = %s
                   AND signal_id = %s
                   AND (
                     (applicant_id IS NULL AND %s IS NULL)
                     OR (applicant_id = %s)
                   )
                """,
                (
                    cache_item["value_str"],
                    cache_item["expires_at"],
                    cache_item["tenant_id"],
                    checkpoint_id_for_cache,
                    cache_item["signal_id"],
                    cache_item["applicant_key"],
                    cache_item["applicant_key"],
                ),
            )
        else:
            cur.execute(
                """
                UPDATE signal_cached_values
                   SET signal_value = %s,
                       expires_at = %s,
                       updated_at = NOW()
                 WHERE tenant_id = %s
                   AND checkpoint_id IS NULL
                   AND signal_id = %s
                   AND (
                     (applicant_id IS NULL AND %s IS NULL)
                     OR (applicant_id = %s)
                   )
                """,
                (
                    cache_item["value_str"],
                    cache_item["expires_at"],
                    cache_item["tenant_id"],
                    cache_item["signal_id"],
                    cache_item["applicant_key"],
                    cache_item["applicant_key"],
                ),
            )
    if budget_override_audit:
        record_promotion_audit(cur, **budget_override_audit)
    conn.commit()
    return outcome, reason
