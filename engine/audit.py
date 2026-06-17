"""Durable signal audit persistence."""

from __future__ import annotations

import uuid
from typing import Any

from .config import logger
from .db import db_cursor


def persist_signal_log(cur, log_item: dict[str, Any]) -> None:
    """Insert one signal_log row and optional param values using the caller connection."""
    cur.execute(
        """
        INSERT INTO signal_log
        (id, decision_log_id, signal_id, applicant_id,
         signal_value, started_at, completed_at,
         cost_incurred, actual_cost_units, success, error_message,
         execution_status, criticality,
         estimated_cost_units, reserved_cost_units, cache_hit, skip_reason_code)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            log_item["signal_log_id"],
            log_item["decision_log_id"],
            log_item["signal_id"],
            log_item["applicant_id"],
            log_item.get("signal_value"),
            log_item["started_at"],
            log_item["completed_at"],
            log_item.get("actual_cost_units", log_item.get("cost_incurred", 0)),
            log_item.get("actual_cost_units", log_item.get("cost_incurred", 0)),
            log_item["success"],
            log_item.get("error_message"),
            log_item.get("execution_status"),
            log_item.get("criticality"),
            log_item.get("estimated_cost_units", 0),
            log_item.get("reserved_cost_units", 0),
            log_item.get("cache_hit", False),
            log_item.get("skip_reason_code"),
        ),
    )
    for param_name, param_value in log_item.get("placeholder_values", {}).items():
        cur.execute(
            """
            INSERT INTO signal_log_values
            (id, signal_log_id, param_name, param_value)
            VALUES (%s, %s, %s, %s)
            """,
            (str(uuid.uuid4()), log_item["signal_log_id"], param_name, str(param_value)),
        )


def persist_signal_logs(cur, log_items: list[dict[str, Any]]) -> None:
    for item in log_items:
        persist_signal_log(cur, item)


def drain_pending_outbox(batch_size: int = 100) -> int:
    """Process any legacy or retry rows in audit_outbox when that table exists."""
    try:
        with db_cursor() as (conn, cur):
            cur.execute(
                """
                SELECT 1 FROM information_schema.tables
                 WHERE table_schema = 'public' AND table_name = 'audit_outbox'
                """
            )
            if not cur.fetchone():
                return 0
            cur.execute(
                """
                SELECT id, payload
                  FROM audit_outbox
                 WHERE status = 'pending'
                 ORDER BY created_at
                 LIMIT %s
                 FOR UPDATE SKIP LOCKED
                """,
                (batch_size,),
            )
            rows = cur.fetchall()
            processed = 0
            for outbox_id, payload in rows:
                try:
                    persist_signal_log(cur, payload)
                    cur.execute(
                        """
                        UPDATE audit_outbox
                           SET status = 'processed',
                               processed_at = NOW(),
                               attempt_count = attempt_count + 1
                         WHERE id = %s
                        """,
                        (outbox_id,),
                    )
                    processed += 1
                except Exception as exc:
                    cur.execute(
                        """
                        UPDATE audit_outbox
                           SET attempt_count = attempt_count + 1,
                               last_error = %s
                         WHERE id = %s
                        """,
                        (str(exc)[:500], outbox_id),
                    )
                    logger.error("Failed to drain audit outbox row %s: %s", outbox_id, exc)
            conn.commit()
            return processed
    except Exception as exc:
        logger.error("Audit outbox drain skipped: %s", exc)
        return 0
