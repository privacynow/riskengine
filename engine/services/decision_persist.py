"""Atomic persistence for completed decision outcomes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..audit import persist_signal_logs


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
    final_decision_value: str,
    total_cost: int,
    pending_signal_logs: list[dict[str, Any]],
    pending_db_cache_writes: list[dict[str, Any]],
) -> None:
    """Write decision_log, signal audit rows, and cache rows in one transaction."""
    cur.execute(
        """
        INSERT INTO decision_log
        (id, checkpoint_id, tenant_id, applicant_id,
         final_decision_value, cost_incurred, correlation_id, decision_timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            decision_id,
            checkpoint_id,
            tenant_id,
            applicant_id,
            final_decision_value,
            total_cost,
            correlation_id,
            decision_timestamp,
        ),
    )
    persist_signal_logs(cur, pending_signal_logs)
    for cache_item in pending_db_cache_writes:
        cur.execute(
            """
            INSERT INTO signal_cached_values
            (id, tenant_id, checkpoint_id, signal_id, applicant_id, signal_value, expires_at)
            VALUES (uuid_generate_v4(), %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                cache_item["tenant_id"],
                cache_item["checkpoint_id"],
                cache_item["signal_id"],
                cache_item["applicant_key"],
                cache_item["value_str"],
                cache_item["expires_at"],
            ),
        )
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
                cache_item["checkpoint_id"],
                cache_item["signal_id"],
                cache_item["applicant_key"],
                cache_item["applicant_key"],
            ),
        )
    conn.commit()
