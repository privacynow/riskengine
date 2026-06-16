import asyncio
import uuid
from typing import Any, Dict

from config import logger
from db import db_cursor

log_queue: asyncio.Queue = asyncio.Queue()


def _process_audit_logging(log_item: Dict[str, Any]):
    with db_cursor() as (conn, cur):
        if log_item["type"] == "signal":
            cur.execute(
                """
                INSERT INTO signal_log
                (id, decision_log_id, signal_id, applicant_id,
                 signal_value, started_at, completed_at,
                 cost_incurred, success)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    log_item["signal_log_id"],
                    log_item["decision_log_id"],
                    log_item["signal_id"],
                    log_item["applicant_id"],
                    log_item["signal_value"],
                    log_item["started_at"],
                    log_item["completed_at"],
                    log_item["cost_incurred"],
                    log_item["success"],
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
        conn.commit()


async def log_processor():
    while True:
        item = await log_queue.get()
        if item is None:
            break
        try:
            _process_audit_logging(item)
        except Exception as exc:
            logger.error("Error processing audit log: %s", exc)
        finally:
            log_queue.task_done()
