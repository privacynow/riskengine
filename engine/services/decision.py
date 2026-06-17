import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from ..cache import in_memory_signal_cache
from ..config import logger
from ..db import db_cursor
from ..models import DecisionRequest, DecisionResponse, DecisionCostSummary, SignalExecutionSummary
from .budget_tracker import BudgetTracker, admit_signals_under_budget
from .decision_persist import persist_decision_outcome
from .dsl import extract_dsl_identifiers
from .execution_planner import (
    DependencyCycleError,
    ExecutionStatus,
    SignalExecutionRecord,
    build_execution_plan,
    compute_actual_cost,
    group_parallel_batches,
    missing_signal_dependencies,
    resolve_outcome,
    should_skip_expensive_after_decline,
    coerce_terminal_decline,
    EXECUTION_ROLE_MANUAL_TEST,
    OutcomeResolution,
    DecisionOutcome,
)
from .signals import coerce_signal_value, invoke_signal
from .templates import extract_placeholders_from_text
from .tenant_budget import (
    finalize_tenant_budget_signal,
    lease_tenant_budget_units,
    load_tenant_budget,
    normalize_override_reason,
    tenant_budget_remaining_units,
)
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
    max_cost: Optional[int],
    budget_override: bool,
):
    """Legacy helper retained for unit tests."""
    if budget_override or max_cost is None:
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


def _cache_checkpoint_id(cache_scope: str, checkpoint_id: str) -> Optional[str]:
    if cache_scope == "tenant_checkpoint_applicant":
        return checkpoint_id
    return None


def _fetch_db_cached_value(
    tenant_id: str,
    checkpoint_id: Optional[str],
    signal_id: str,
    applicant_key: str | None,
    cache_scope: str,
) -> tuple[str, datetime] | None:
    with db_cursor() as (_, cur):
        if cache_scope == "tenant_checkpoint_applicant":
            cur.execute(
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
                (tenant_id, checkpoint_id, signal_id, applicant_key, applicant_key),
            )
        else:
            cur.execute(
                """
                SELECT signal_value, expires_at
                  FROM signal_cached_values
                 WHERE tenant_id = %s
                   AND checkpoint_id IS NULL
                   AND signal_id = %s
                   AND (
                     (applicant_id IS NULL AND %s IS NULL)
                     OR (applicant_id = %s)
                   )
                """,
                (tenant_id, signal_id, applicant_key, applicant_key),
            )
        row = cur.fetchone()
        if not row:
            return None
        val_str, expires_at = row
        if datetime.utcnow() >= expires_at:
            return None
        return val_str, expires_at


@dataclass(frozen=True)
class DecisionExecutionContext:
    cp_row: CheckpointRow
    checkpoint_id: str
    dsl_expression: str
    max_cost: Optional[int]
    budget_exceeded_policy: str
    vendor_failure_policy: str
    terminal_decline_signal_names: tuple[str, ...]
    timeout_seconds: int
    signals: List[ExecutableSignalRow]


def load_decision_execution_context(
    tenant_id: str,
    request: DecisionRequest,
    checkpoint_id: Optional[str] = None,
) -> DecisionExecutionContext:
    with db_cursor() as (_, cur):
        if checkpoint_id:
            cp_row = fetch_checkpoint_row_by_id(cur, tenant_id, checkpoint_id)
        else:
            cp_row = fetch_current_checkpoint_row(cur, tenant_id, request.checkpoint_name)
        resolved_checkpoint_id = cp_row.id
        signals = fetch_executable_signal_rows(cur, tenant_id, resolved_checkpoint_id)
    return DecisionExecutionContext(
        cp_row=cp_row,
        checkpoint_id=resolved_checkpoint_id,
        dsl_expression=cp_row.dsl_expression,
        max_cost=cp_row.max_cost,
        budget_exceeded_policy=cp_row.budget_exceeded_policy,
        vendor_failure_policy=cp_row.vendor_failure_policy,
        terminal_decline_signal_names=cp_row.terminal_decline_signal_names,
        timeout_seconds=cp_row.timeout_seconds,
        signals=signals,
    )


def _record_skip(
    *,
    row: ExecutableSignalRow,
    status: ExecutionStatus,
    records: Dict[str, SignalExecutionRecord],
    decision_id: str,
    applicant_id: Optional[str],
    pending_logs: list,
    skip_reason: str,
) -> None:
    now = datetime.utcnow()
    rec = SignalExecutionRecord(
        name=row.name,
        signal_id=row.id,
        status=status,
        criticality=row.criticality,
        estimated_cost_units=row.cost,
        skip_reason_code=skip_reason,
    )
    records[row.name] = rec
    pending_logs.append(
        {
            "signal_log_id": str(uuid.uuid4()),
            "decision_log_id": decision_id,
            "signal_id": row.id,
            "applicant_id": applicant_id,
            "signal_value": None,
            "started_at": now,
            "completed_at": now,
            "actual_cost_units": 0,
            "cost_incurred": 0,
            "success": False,
            "execution_status": status.value,
            "criticality": row.criticality,
            "estimated_cost_units": row.cost,
            "reserved_cost_units": 0,
            "cache_hit": False,
            "skip_reason_code": skip_reason,
            "error_message": skip_reason,
            "placeholder_values": {},
        }
    )


async def execute_decision(
    tenant_id: str,
    request: DecisionRequest,
    actor_id: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
    *,
    include_manual_test: bool = False,
    budget_override: bool = False,
    override_reason: Optional[str] = None,
) -> DecisionResponse:
    ctx = load_decision_execution_context(tenant_id, request, checkpoint_id)
    cp_row = ctx.cp_row
    checkpoint_id = ctx.checkpoint_id
    dsl_expression = ctx.dsl_expression
    signals = ctx.signals
    signals_by_name = {s.name: s for s in signals}
    all_signal_names = set(signals_by_name.keys())
    dsl_required_names = extract_dsl_identifiers(dsl_expression) & all_signal_names

    decision_id = str(uuid.uuid4())
    decision_started_at = datetime.utcnow()
    checkpoint_deadline = (
        time.monotonic() + cp_row.timeout_seconds if cp_row.timeout_seconds > 0 else None
    )

    user_params = request.parameters or {}
    checkpoint_timed_out = False
    terminal_decline = False
    terminal_names = set(ctx.terminal_decline_signal_names)

    records: Dict[str, SignalExecutionRecord] = {}
    produced: Dict[str, Any] = {}
    pending_signal_logs: list[dict[str, Any]] = []
    pending_memory_cache_writes: list[tuple[Any, ...]] = []
    pending_db_cache_writes: list[dict[str, Any]] = []

    tenant_budget = load_tenant_budget(tenant_id)
    budget_tracker = BudgetTracker(
        checkpoint_cap=ctx.max_cost,
        tenant_limit=tenant_budget.limit_units if tenant_budget else None,
        tenant_used=(
            tenant_budget.used_units + tenant_budget.reserved_units if tenant_budget else 0
        ),
        budget_override=budget_override,
    )
    use_tenant_db_leases = tenant_budget is not None and not budget_override

    override_audit: dict[str, Any] | None = None
    if budget_override:
        reason = normalize_override_reason(override_reason)
        override_audit = {
            "tenant_id": tenant_id,
            "resource_type": "test_decision",
            "resource_id": checkpoint_id,
            "resource_name": cp_row.name,
            "actor_id": actor_id or "unknown",
            "promotion_reason": reason,
            "action": "budget_override",
            "source": "test_lab",
        }

    try:
        ordered_names, execution_set, _graph = build_execution_plan(
            dsl_expression=dsl_expression,
            signals=signals,
            include_manual_test=include_manual_test,
        )
    except DependencyCycleError as exc:
        logger.error("Dependency cycle in checkpoint %s: %s", checkpoint_id, exc)
        resolution = OutcomeResolution(DecisionOutcome.ERROR, "dependency_cycle")
        cost_summary = DecisionCostSummary(
            estimated_units=0,
            reserved_units=0,
            actual_units=0,
            budget_units=ctx.max_cost,
            tenant_budget_remaining_units=budget_tracker.tenant_remaining_after_commit,
        )
        with db_cursor() as (conn, cur):
            persist_decision_outcome(
                conn,
                cur,
                decision_id=decision_id,
                checkpoint_id=checkpoint_id,
                tenant_id=tenant_id,
                applicant_id=request.applicant_id,
                correlation_id=request.correlation_id,
                decision_timestamp=decision_started_at,
                decision_outcome=resolution.outcome.value,
                decision_reason=resolution.reason,
                degraded=False,
                estimated_cost_units=0,
                reserved_cost_units=0,
                actual_cost_units=0,
                budget_units=ctx.max_cost,
                pending_signal_logs=[],
                pending_db_cache_writes=[],
                tenant_budget_apply_units=0,
                budget_override_audit=override_audit,
            )
        return DecisionResponse(
            decision_id=decision_id,
            decision_outcome=resolution.outcome.value,
            decision_reason=resolution.reason,
            degraded=False,
            cost=cost_summary,
            signals=[],
            signal_results={},
        )

    estimated_total = sum(signals_by_name[name].cost for name in execution_set)

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

    async def run_signal(row: ExecutableSignalRow) -> SignalExecutionRecord:
        nonlocal terminal_decline
        reserved_units = row.cost
        started = datetime.utcnow()
        success = True
        value = None
        error_message: Optional[str] = None
        cache_hit = False
        attempt_started = False
        db_leased_units = 0

        placeholders_list = set()
        for tmpl in (
            row.request_url_params_template,
            row.request_body_template,
            row.request_headers_template,
            row.function_params_template,
        ):
            placeholders_list.update(extract_placeholders_from_text(tmpl or ""))
        if row.type == "expression" and row.expression_body:
            placeholders_list.update(extract_dsl_identifiers(row.expression_body))

        partial_params = {p: user_params[p] for p in sorted(placeholders_list) if p in user_params}
        context = dict(produced)
        context.update(partial_params)

        if checkpoint_time_exhausted():
            rec = SignalExecutionRecord(
                name=row.name,
                signal_id=row.id,
                status=ExecutionStatus.FAILED,
                criticality=row.criticality,
                estimated_cost_units=row.cost,
                error_message="checkpoint_timeout",
            )
            pending_signal_logs.append(
                _log_payload(decision_id, request.applicant_id, row, rec, started, partial_params)
            )
            budget_tracker.commit_actual(reserved_units=reserved_units, actual_units=0)
            return rec

        timeout = effective_signal_timeout(row)
        if timeout <= 0:
            rec = SignalExecutionRecord(
                name=row.name,
                signal_id=row.id,
                status=ExecutionStatus.FAILED,
                criticality=row.criticality,
                estimated_cost_units=row.cost,
                error_message="checkpoint_timeout",
            )
            pending_signal_logs.append(
                _log_payload(decision_id, request.applicant_id, row, rec, started, partial_params)
            )
            budget_tracker.commit_actual(reserved_units=reserved_units, actual_units=0)
            return rec

        applicant_key = None if row.global_reuse else request.applicant_id
        cache_ckpt = _cache_checkpoint_id(row.cache_scope, checkpoint_id)
        if row.allow_caching:
            cached_val = in_memory_signal_cache.get(
                tenant_id, cache_ckpt, applicant_key, row.id, row.cache_scope
            )
            if cached_val is not None:
                value = coerce_signal_value(cached_val)
                cache_hit = True
            else:
                cached = _fetch_db_cached_value(
                    tenant_id, cache_ckpt, row.id, applicant_key, row.cache_scope
                )
                if cached is not None:
                    val_str, _expires_at = cached
                    value = coerce_signal_value(val_str)
                    cache_hit = True
                    in_memory_signal_cache.set(
                        tenant_id,
                        cache_ckpt,
                        applicant_key,
                        row.id,
                        val_str,
                        row.cache_expiration_seconds,
                        row.cache_scope,
                    )

        if value is None:
            if use_tenant_db_leases:
                if not lease_tenant_budget_units(tenant_id, row.cost):
                    budget_tracker.release_reserve(reserved_units)
                    rec = SignalExecutionRecord(
                        name=row.name,
                        signal_id=row.id,
                        status=ExecutionStatus.SKIPPED_BUDGET,
                        criticality=row.criticality,
                        estimated_cost_units=row.cost,
                        skip_reason_code="tenant_budget_exceeded",
                    )
                    pending_signal_logs.append(
                        _log_payload(
                            decision_id, request.applicant_id, row, rec, started, partial_params
                        )
                    )
                    return rec
                db_leased_units = row.cost
            attempt_started = True
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
                logger.error("Signal %s timed out", row.name)
                success = False
                value = None
                error_message = "signal_timeout"
            except Exception as exc:
                logger.error("Error invoking signal %s: %s", row.name, exc)
                success = False
                value = None
                error_message = str(exc)

            if row.allow_caching and success and value is not None:
                val_str = str(value)
                expires_at = datetime.utcnow() + timedelta(seconds=row.cache_expiration_seconds)
                pending_memory_cache_writes.append(
                    (
                        tenant_id,
                        cache_ckpt,
                        applicant_key,
                        row.id,
                        value,
                        row.cache_expiration_seconds,
                        row.cache_scope,
                    )
                )
                pending_db_cache_writes.append(
                    {
                        "tenant_id": tenant_id,
                        "checkpoint_id": cache_ckpt,
                        "signal_id": row.id,
                        "applicant_key": applicant_key,
                        "value_str": val_str,
                        "expires_at": expires_at,
                        "cache_scope": row.cache_scope,
                    }
                )

        actual = compute_actual_cost(
            row, success=success, attempt_started=attempt_started, cache_hit=cache_hit
        )
        if db_leased_units > 0:
            finalize_tenant_budget_signal(tenant_id, db_leased_units, actual)
            budget_tracker.tenant_actual_charged += actual
        budget_tracker.commit_actual(reserved_units=reserved_units, actual_units=actual)

        if success and value is not None:
            produced[row.name] = coerce_signal_value(value)
            if row.name in terminal_names and coerce_terminal_decline(row.name, value):
                terminal_decline = True
            status = ExecutionStatus.RAN
        else:
            status = ExecutionStatus.FAILED

        rec = SignalExecutionRecord(
            name=row.name,
            signal_id=row.id,
            status=status,
            criticality=row.criticality,
            estimated_cost_units=row.cost,
            reserved_cost_units=reserved_units,
            actual_cost_units=actual,
            cache_hit=cache_hit,
            value=produced.get(row.name),
            error_message=error_message,
        )
        pending_signal_logs.append(
            _log_payload(decision_id, request.applicant_id, row, rec, started, partial_params)
        )
        return rec

    def _log_payload(decision_id, applicant_id, row, rec, started, partial_params):
        ended = datetime.utcnow()
        return {
            "signal_log_id": str(uuid.uuid4()),
            "decision_log_id": decision_id,
            "signal_id": row.id,
            "applicant_id": applicant_id,
            "signal_value": str(rec.value) if rec.value is not None else None,
            "started_at": started,
            "completed_at": ended,
            "actual_cost_units": rec.actual_cost_units,
            "cost_incurred": rec.actual_cost_units,
            "success": rec.status == ExecutionStatus.RAN,
            "execution_status": rec.status.value,
            "criticality": rec.criticality,
            "estimated_cost_units": rec.estimated_cost_units,
            "reserved_cost_units": rec.reserved_cost_units,
            "cache_hit": rec.cache_hit,
            "skip_reason_code": rec.skip_reason_code,
            "error_message": rec.error_message,
            "placeholder_values": partial_params,
        }

    batches = group_parallel_batches(ordered_names, signals_by_name)

    for batch_names in batches:
        if checkpoint_time_exhausted():
            break

        candidates: List[ExecutableSignalRow] = []
        for name in batch_names:
            row = signals_by_name[name]
            if name in records:
                continue
            if row.execution_role == EXECUTION_ROLE_MANUAL_TEST and not include_manual_test:
                _record_skip(
                    row=row,
                    status=ExecutionStatus.NOT_APPLICABLE,
                    records=records,
                    decision_id=decision_id,
                    applicant_id=request.applicant_id,
                    pending_logs=pending_signal_logs,
                    skip_reason="manual_test_only",
                )
                continue
            if name not in execution_set:
                _record_skip(
                    row=row,
                    status=ExecutionStatus.NOT_APPLICABLE,
                    records=records,
                    decision_id=decision_id,
                    applicant_id=request.applicant_id,
                    pending_logs=pending_signal_logs,
                    skip_reason="not_referenced",
                )
                continue
            missing = missing_signal_dependencies(row, produced, all_signal_names)
            if missing:
                _record_skip(
                    row=row,
                    status=ExecutionStatus.SKIPPED_DEPENDENCY,
                    records=records,
                    decision_id=decision_id,
                    applicant_id=request.applicant_id,
                    pending_logs=pending_signal_logs,
                    skip_reason="dependency_not_produced",
                )
                continue
            if should_skip_expensive_after_decline(row, terminal_decline):
                _record_skip(
                    row=row,
                    status=ExecutionStatus.SKIPPED_CONDITION,
                    records=records,
                    decision_id=decision_id,
                    applicant_id=request.applicant_id,
                    pending_logs=pending_signal_logs,
                    skip_reason="terminal_decline_path",
                )
                continue
            candidates.append(row)

        runnable, budget_skipped = admit_signals_under_budget(candidates, budget_tracker)
        for row in budget_skipped:
            _record_skip(
                row=row,
                status=ExecutionStatus.SKIPPED_BUDGET,
                records=records,
                decision_id=decision_id,
                applicant_id=request.applicant_id,
                pending_logs=pending_signal_logs,
                skip_reason="budget_exceeded",
            )

        if not runnable:
            continue

        if len(runnable) == 1 or not runnable[0].can_run_in_parallel:
            for row in runnable:
                if checkpoint_time_exhausted():
                    break
                records[row.name] = await run_signal(row)
        else:
            if checkpoint_time_exhausted():
                for row in runnable:
                    budget_tracker.release_reserve(row.cost)
                    _record_skip(
                        row=row,
                        status=ExecutionStatus.FAILED,
                        records=records,
                        decision_id=decision_id,
                        applicant_id=request.applicant_id,
                        pending_logs=pending_signal_logs,
                        skip_reason="checkpoint_timeout",
                    )
                continue
            remaining = remaining_checkpoint_seconds()
            tasks = {asyncio.create_task(run_signal(sig)): sig for sig in runnable}
            if remaining is not None:
                done, pending = await asyncio.wait(tasks.keys(), timeout=max(0.001, remaining))
            else:
                done, pending = await asyncio.wait(tasks.keys())
            for task in done:
                rec = task.result()
                records[rec.name] = rec
            if pending:
                checkpoint_timed_out = True
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                for task in pending:
                    sig = tasks[task]
                    if sig.name not in records:
                        budget_tracker.release_reserve(sig.cost)
                        _record_skip(
                            row=sig,
                            status=ExecutionStatus.FAILED,
                            records=records,
                            decision_id=decision_id,
                            applicant_id=request.applicant_id,
                            pending_logs=pending_signal_logs,
                            skip_reason="checkpoint_timeout",
                        )

    engine_error = False
    resolution = resolve_outcome(
        dsl_expression=dsl_expression,
        produced=produced,
        records=records,
        dsl_required_names=dsl_required_names,
        budget_exceeded_policy=ctx.budget_exceeded_policy,
        vendor_failure_policy=ctx.vendor_failure_policy,
        checkpoint_timed_out=checkpoint_timed_out,
        engine_error=engine_error,
    )

    signal_summaries = [
        SignalExecutionSummary(**records[name].to_api_dict())
        for name in ordered_names
        if name in records
    ]

    tenant_remaining = tenant_budget_remaining_units(tenant_id) if tenant_budget else None
    cost_summary = DecisionCostSummary(
        estimated_units=estimated_total,
        reserved_units=budget_tracker.checkpoint_total_reserved,
        actual_units=budget_tracker.checkpoint_actual,
        budget_units=ctx.max_cost,
        tenant_budget_remaining_units=tenant_remaining,
    )

    with db_cursor() as (conn, cur):
        persist_outcome, persist_reason = persist_decision_outcome(
            conn,
            cur,
            decision_id=decision_id,
            checkpoint_id=checkpoint_id,
            tenant_id=tenant_id,
            applicant_id=request.applicant_id,
            correlation_id=request.correlation_id,
            decision_timestamp=decision_started_at,
            decision_outcome=resolution.outcome.value,
            decision_reason=resolution.reason,
            degraded=resolution.degraded,
            estimated_cost_units=estimated_total,
            reserved_cost_units=budget_tracker.checkpoint_total_reserved,
            actual_cost_units=budget_tracker.checkpoint_actual,
            budget_units=ctx.max_cost,
            pending_signal_logs=pending_signal_logs,
            pending_db_cache_writes=pending_db_cache_writes,
            tenant_budget_apply_units=(
                budget_tracker.checkpoint_actual
                if tenant_budget and budget_override
                else 0
            ),
            budget_override_audit=override_audit,
        )

    if persist_outcome != resolution.outcome.value:
        resolution = OutcomeResolution(
            DecisionOutcome(persist_outcome),
            persist_reason,
            degraded=resolution.degraded,
        )
        cost_summary = DecisionCostSummary(
            estimated_units=estimated_total,
            reserved_units=budget_tracker.checkpoint_total_reserved,
            actual_units=budget_tracker.checkpoint_actual,
            budget_units=ctx.max_cost,
            tenant_budget_remaining_units=tenant_budget_remaining_units(tenant_id)
            if tenant_budget
            else None,
        )

    for item in pending_memory_cache_writes:
        tenant_id_c, cache_ckpt, applicant_key, signal_id, value, ttl, cache_scope = item
        in_memory_signal_cache.set(
            tenant_id_c, cache_ckpt, applicant_key, signal_id, value, ttl, cache_scope
        )

    return DecisionResponse(
        decision_id=decision_id,
        decision_outcome=resolution.outcome.value,
        decision_reason=resolution.reason,
        degraded=resolution.degraded,
        cost=cost_summary,
        signals=signal_summaries,
        signal_results={k: v for k, v in produced.items()},
    )
