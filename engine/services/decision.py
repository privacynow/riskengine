import asyncio
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..audit import log_queue
from ..cache import in_memory_signal_cache
from ..config import logger
from ..models import DecisionRequest, DecisionResponse
from .dsl import evaluate_expression, extract_dsl_identifiers
from .signals import coerce_signal_value, invoke_signal
from .templates import extract_placeholders_from_text
from .tenancy import (
    CheckpointRow,
    ExecutableSignalRow,
    fetch_checkpoint_row_by_id,
    fetch_current_checkpoint_row,
    fetch_executable_signal_rows,
)


def partition_signals_by_cost(
    signals: List[ExecutableSignalRow],
    total_cost: int,
    max_cost: int,
    override_cost_flag: bool,
) -> Tuple[List[ExecutableSignalRow], List[ExecutableSignalRow]]:
    """Split a same-order group into runnable vs skipped signals under the cost budget."""
    if override_cost_flag:
        return signals, []

    runnable: List[ExecutableSignalRow] = []
    skipped: List[ExecutableSignalRow] = []
    budget = total_cost
    for sig in signals:
        if budget + sig.cost > max_cost:
            skipped.append(sig)
        else:
            runnable.append(sig)
            budget += sig.cost
    return runnable, skipped


async def execute_decision(
    conn,
    cur,
    tenant_id: str,
    request: DecisionRequest,
    actor_id: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
) -> DecisionResponse:
    if checkpoint_id:
        cp_row: CheckpointRow = fetch_checkpoint_row_by_id(cur, tenant_id, checkpoint_id)
    else:
        cp_row = fetch_current_checkpoint_row(cur, tenant_id, request.checkpoint_name)
    checkpoint_id = cp_row.id
    dsl_expression = cp_row.dsl_expression
    max_cost = cp_row.max_cost
    override_cost_flag = cp_row.override_cost_flag
    checkpoint_deadline = (
        time.monotonic() + cp_row.timeout_seconds if cp_row.timeout_seconds > 0 else None
    )

    decision_id = str(uuid.uuid4())
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
            request.applicant_id,
            "PENDING",
            0,
            request.correlation_id,
            datetime.utcnow(),
        ),
    )
    conn.commit()

    signals = fetch_executable_signal_rows(cur, tenant_id, checkpoint_id)
    total_cost = 0
    signal_results: Dict[str, Any] = {}
    user_params = request.parameters or {}
    checkpoint_timed_out = False

    signals_by_order: Dict[int, list] = defaultdict(list)
    for signal in signals:
        signals_by_order[signal.order_of_evaluation].append(signal)

    def remaining_checkpoint_seconds() -> Optional[float]:
        if checkpoint_deadline is None:
            return None
        return checkpoint_deadline - time.monotonic()

    def checkpoint_time_exhausted() -> bool:
        nonlocal checkpoint_timed_out
        remaining = remaining_checkpoint_seconds()
        if remaining is not None and remaining <= 0:
            checkpoint_timed_out = True
            return True
        return False

    def effective_signal_timeout(row: ExecutableSignalRow) -> float:
        per_signal = max(1, row.timeout_seconds or 30)
        remaining = remaining_checkpoint_seconds()
        if remaining is None:
            return per_signal
        if remaining <= 0:
            return 0.0
        return min(per_signal, remaining)

    async def log_skipped_signal(
        row: ExecutableSignalRow,
        *,
        error_message: str,
        partial_params: Dict[str, Any],
    ) -> None:
        now = datetime.utcnow()
        await log_queue.put(
            {
                "type": "signal",
                "signal_log_id": str(uuid.uuid4()),
                "decision_log_id": decision_id,
                "signal_id": row.id,
                "applicant_id": request.applicant_id,
                "signal_value": "False",
                "started_at": now,
                "completed_at": now,
                "cost_incurred": 0,
                "success": False,
                "placeholder_values": partial_params,
                "actor_id": actor_id,
                "error_message": error_message,
            }
        )

    async def record_skipped_signal(row: ExecutableSignalRow, error_message: str) -> None:
        now = datetime.utcnow()
        signal_results[row.name] = False
        await log_queue.put(
            {
                "type": "signal",
                "signal_log_id": str(uuid.uuid4()),
                "decision_log_id": decision_id,
                "signal_id": row.id,
                "applicant_id": request.applicant_id,
                "signal_value": "False",
                "started_at": now,
                "completed_at": now,
                "cost_incurred": 0,
                "success": False,
                "placeholder_values": {},
                "actor_id": actor_id,
                "error_message": error_message,
            }
        )

    async def run_signal(row: ExecutableSignalRow):
        started = datetime.utcnow()
        success = True
        value = None
        error_message: Optional[str] = None

        placeholders_list = set()
        for tmpl in [
            row.request_url_params_template,
            row.request_body_template,
            row.request_headers_template,
            row.function_params_template,
        ]:
            placeholders_list.update(extract_placeholders_from_text(tmpl or ""))
        if row.type == "expression" and row.expression_body:
            placeholders_list.update(extract_dsl_identifiers(row.expression_body))

        partial_params = {
            p: user_params[p] for p in sorted(placeholders_list) if p in user_params
        }
        context = dict(signal_results)
        context.update(partial_params)

        if checkpoint_time_exhausted():
            await log_skipped_signal(
                row,
                error_message="checkpoint_timeout",
                partial_params=partial_params,
            )
            return row.name, False, 0

        timeout = effective_signal_timeout(row)
        if timeout <= 0:
            await log_skipped_signal(
                row,
                error_message="checkpoint_timeout",
                partial_params=partial_params,
            )
            return row.name, False, 0

        applicant_key = None if row.global_reuse else request.applicant_id
        if row.allow_caching:
            cached_val = in_memory_signal_cache.get(
                tenant_id, checkpoint_id, applicant_key, row.id
            )
            if cached_val is not None:
                value = coerce_signal_value(cached_val)
            else:
                cur2 = conn.cursor()
                cur2.execute(
                    """
                    SELECT signal_value, expires_at
                      FROM signal_cached_values
                     WHERE tenant_id = %s
                       AND checkpoint_id = %s
                       AND signal_id = %s
                       AND (
                         (applicant_id IS NULL AND %s IS NULL)
                         OR (applicant_id = %s)
                       )
                    """,
                    (
                        tenant_id,
                        checkpoint_id,
                        row.id,
                        applicant_key,
                        applicant_key,
                    ),
                )
                crow = cur2.fetchone()
                if crow:
                    val_str, expires_at = crow
                    if datetime.utcnow() < expires_at:
                        value = coerce_signal_value(val_str)
                        in_memory_signal_cache.set(
                            tenant_id,
                            checkpoint_id,
                            applicant_key,
                            row.id,
                            val_str,
                            row.cache_expiration_seconds,
                        )
                cur2.close()

        if value is None:
            try:
                value = await asyncio.wait_for(
                    invoke_signal(
                        signal_type=row.type,
                        method_of_call=row.method_of_call or "",
                        expression_body=row.expression_body,
                        invoke_context=context,
                        http_method=row.http_method,
                        url_params_template=row.request_url_params_template,
                        body_template=row.request_body_template,
                        headers_template=row.request_headers_template,
                        bearer_token=row.bearer_token,
                        function_params_template=row.function_params_template,
                        signal_id=row.id,
                        timeout_seconds=int(max(1, timeout)),
                    ),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Signal %s timed out after %.2fs (checkpoint remaining %.2fs)",
                    row.name,
                    timeout,
                    remaining_checkpoint_seconds() or -1,
                )
                success = False
                value = False
                error_message = "signal_timeout"
            except Exception as exc:
                logger.error("Error invoking signal %s: %s", row.name, exc)
                success = False
                value = False
                error_message = str(exc)

            if row.allow_caching and success:
                in_memory_signal_cache.set(
                    tenant_id,
                    checkpoint_id,
                    applicant_key,
                    row.id,
                    value,
                    row.cache_expiration_seconds,
                )
                cur3 = conn.cursor()
                expires_at = datetime.utcnow() + timedelta(seconds=row.cache_expiration_seconds)
                val_str = str(value)
                cur3.execute(
                    """
                    INSERT INTO signal_cached_values
                    (id, tenant_id, checkpoint_id, signal_id, applicant_id, signal_value, expires_at)
                    VALUES (uuid_generate_v4(), %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (tenant_id, checkpoint_id, row.id, applicant_key, val_str, expires_at),
                )
                cur3.execute(
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
                        val_str,
                        expires_at,
                        tenant_id,
                        checkpoint_id,
                        row.id,
                        applicant_key,
                        applicant_key,
                    ),
                )
                conn.commit()
                cur3.close()

        ended = datetime.utcnow()
        await log_queue.put(
            {
                "type": "signal",
                "signal_log_id": str(uuid.uuid4()),
                "decision_log_id": decision_id,
                "signal_id": row.id,
                "applicant_id": request.applicant_id,
                "signal_value": str(value),
                "started_at": started,
                "completed_at": ended,
                "cost_incurred": row.cost if success else 0,
                "success": success,
                "placeholder_values": partial_params,
                "actor_id": actor_id,
                "error_message": error_message,
            }
        )
        return row.name, value, row.cost if success else 0

    async def run_parallel_batch(batch: List[ExecutableSignalRow]):
        nonlocal total_cost, checkpoint_timed_out
        if checkpoint_time_exhausted():
            for sig in batch:
                if sig.name not in signal_results:
                    await record_skipped_signal(sig, "checkpoint_timeout")
            return

        remaining = remaining_checkpoint_seconds()
        tasks = {asyncio.create_task(run_signal(sig)): sig for sig in batch}
        done: set[asyncio.Task]
        pending: set[asyncio.Task]

        if remaining is not None:
            done, pending = await asyncio.wait(tasks.keys(), timeout=max(0.001, remaining))
        else:
            done, pending = await asyncio.wait(tasks.keys())

        for task in done:
            name, val, cost = task.result()
            signal_results[name] = coerce_signal_value(val)
            total_cost += cost

        if pending:
            checkpoint_timed_out = True
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in pending:
                sig = tasks[task]
                if sig.name not in signal_results:
                    await record_skipped_signal(sig, "checkpoint_timeout")

    async def run_serial(sig: ExecutableSignalRow):
        nonlocal total_cost
        name, val, cost = await run_signal(sig)
        signal_results[name] = coerce_signal_value(val)
        total_cost += cost

    for order_val in sorted(signals_by_order.keys()):
        if checkpoint_time_exhausted():
            for sig in signals_by_order[order_val]:
                if sig.name not in signal_results:
                    await record_skipped_signal(sig, "checkpoint_timeout")
            continue

        group = signals_by_order[order_val]
        runnable, skipped = partition_signals_by_cost(
            group, total_cost, max_cost, override_cost_flag
        )
        for sig in skipped:
            await record_skipped_signal(sig, "cost_budget_exceeded")

        parallel_batch: List[ExecutableSignalRow] = []
        for sig in runnable:
            if checkpoint_time_exhausted():
                await record_skipped_signal(sig, "checkpoint_timeout")
                continue
            if sig.can_run_in_parallel:
                parallel_batch.append(sig)
                continue
            if parallel_batch:
                await run_parallel_batch(parallel_batch)
                parallel_batch = []
            await run_serial(sig)
        if parallel_batch:
            await run_parallel_batch(parallel_batch)

    if checkpoint_time_exhausted():
        final_eval = False
    else:
        try:
            final_eval = evaluate_expression(dsl_expression, signal_results)
        except Exception as exc:
            logger.error("Error evaluating DSL expression: %s", exc)
            final_eval = False

    final_decision_val = str(final_eval)
    cur.execute(
        """
        UPDATE decision_log
           SET final_decision_value = %s,
               cost_incurred = %s,
               updated_at = NOW()
         WHERE id = %s
        """,
        (final_decision_val, total_cost, decision_id),
    )
    conn.commit()

    return DecisionResponse(
        decision_id=decision_id,
        final_decision_value=final_decision_val,
        cost_incurred=total_cost,
        signal_results=signal_results,
    )
