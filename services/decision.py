import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from audit import log_queue
from cache import in_memory_signal_cache
from config import logger
from models import DecisionRequest, DecisionResponse
from services.security import create_restricted_evaluator
from services.signals import coerce_signal_value, invoke_signal
from services.templates import extract_placeholders_from_text
from services.tenancy import (
    CheckpointRow,
    ExecutableSignalRow,
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
) -> DecisionResponse:
    cp_row: CheckpointRow = fetch_current_checkpoint_row(cur, tenant_id, request.checkpoint_name)
    checkpoint_id = cp_row.id
    dsl_expression = cp_row.dsl_expression
    max_cost = cp_row.max_cost
    override_cost_flag = cp_row.override_cost_flag

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

    signals_by_order: Dict[int, list] = defaultdict(list)
    for signal in signals:
        signals_by_order[signal.order_of_evaluation].append(signal)

    async def run_signal(row: ExecutableSignalRow):
        started = datetime.utcnow()
        success = True
        value = None

        placeholders_list = set()
        for tmpl in [
            row.request_url_params_template,
            row.request_body_template,
            row.request_headers_template,
            row.function_params_template,
        ]:
            placeholders_list.update(extract_placeholders_from_text(tmpl or ""))

        partial_params = {
            p: user_params[p] for p in sorted(placeholders_list) if p in user_params
        }
        context = dict(signal_results)
        context.update(partial_params)

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
                value = await invoke_signal(
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
                )
            except Exception as exc:
                logger.error("Error invoking signal %s: %s", row.name, exc)
                success = False
                value = False

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
            }
        )
        return row.name, value, row.cost if success else 0

    for order_val in sorted(signals_by_order.keys()):
        group = signals_by_order[order_val]
        runnable, skipped = partition_signals_by_cost(
            group, total_cost, max_cost, override_cost_flag
        )
        for sig in skipped:
            signal_results[sig.name] = False

        if override_cost_flag:
            results = await asyncio.gather(*(run_signal(sig) for sig in runnable))
            for name, val, cost in results:
                signal_results[name] = coerce_signal_value(val)
                total_cost += cost
        else:
            for sig in runnable:
                name, val, cost = await run_signal(sig)
                signal_results[name] = coerce_signal_value(val)
                total_cost += cost

    try:
        evaluator = create_restricted_evaluator(signal_results)
        final_eval = evaluator.eval(dsl_expression)
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
