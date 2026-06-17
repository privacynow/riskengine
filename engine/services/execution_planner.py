"""Deterministic execution planner for checkpoint decisions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

from .dsl import evaluate_expression, extract_dsl_identifiers
from .templates import extract_placeholders_from_text

CRITICALITY_ORDER = {"required": 0, "preferred": 1, "optional": 2}

EXECUTION_ROLE_REFERENCED = "referenced_policy"
EXECUTION_ROLE_ALWAYS_AUDIT = "always_run_audit"
EXECUTION_ROLE_MANUAL_TEST = "manual_test_only"


class ExecutionStatus(str, Enum):
    RAN = "ran"
    SKIPPED_BUDGET = "skipped_budget"
    SKIPPED_CONDITION = "skipped_condition"
    SKIPPED_DEPENDENCY = "skipped_dependency"
    SKIPPED_CACHE_POLICY = "skipped_cache_policy"
    NOT_APPLICABLE = "not_applicable"
    NOT_EVALUATED = "not_evaluated"
    FAILED = "failed"


class DecisionOutcome(str, Enum):
    APPROVE = "APPROVE"
    DECLINE = "DECLINE"
    REFER = "REFER"
    INCOMPLETE = "INCOMPLETE"
    ERROR = "ERROR"


@dataclass
class SignalExecutionRecord:
    name: str
    signal_id: str
    status: ExecutionStatus
    criticality: str
    estimated_cost_units: int = 0
    reserved_cost_units: int = 0
    actual_cost_units: int = 0
    cache_hit: bool = False
    skip_reason_code: Optional[str] = None
    value: Any = None
    error_message: Optional[str] = None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "criticality": self.criticality,
            "estimated_cost_units": self.estimated_cost_units,
            "reserved_cost_units": self.reserved_cost_units,
            "actual_cost_units": self.actual_cost_units,
            "cache_hit": self.cache_hit,
            "skip_reason": self.skip_reason_code,
            "value": self.value,
        }


@dataclass
class CostSummary:
    estimated_units: int = 0
    reserved_units: int = 0
    actual_units: int = 0
    budget_units: Optional[int] = None
    tenant_budget_remaining_units: Optional[int] = None


@dataclass
class OutcomeResolution:
    outcome: DecisionOutcome
    reason: str
    degraded: bool = False


@dataclass
class PlannerRuntimeState:
    terminal_decline: bool = False
    produced: Dict[str, Any] = field(default_factory=dict)
    records: Dict[str, SignalExecutionRecord] = field(default_factory=dict)
    actual_cost: int = 0
    reserved_cost: int = 0
    estimated_cost: int = 0
    degraded: bool = False


def signal_dependency_names(signal: Any) -> Set[str]:
    """Identifiers this signal needs from prior results or request params."""
    names: Set[str] = set()
    if getattr(signal, "type", None) == "expression" and signal.expression_body:
        names.update(extract_dsl_identifiers(signal.expression_body))
    for tmpl in (
        signal.request_url_params_template,
        signal.request_body_template,
        signal.request_headers_template,
        signal.function_params_template,
    ):
        names.update(extract_placeholders_from_text(tmpl or ""))
    return names


def build_dependency_graph(
    signals_by_name: Mapping[str, Any],
) -> Dict[str, Set[str]]:
    graph: Dict[str, Set[str]] = {}
    for name, sig in signals_by_name.items():
        deps = signal_dependency_names(sig) & set(signals_by_name.keys())
        graph[name] = deps
    return graph


def _closure_from_roots(
    roots: Set[str],
    graph: Mapping[str, Set[str]],
) -> Set[str]:
    needed: Set[str] = set()
    stack = list(roots)
    while stack:
        node = stack.pop()
        if node in needed or node not in graph:
            continue
        needed.add(node)
        stack.extend(graph.get(node, ()))
    return needed


def compute_execution_set(
    *,
    dsl_expression: str,
    signals_by_name: Mapping[str, Any],
    include_manual_test: bool,
) -> Set[str]:
    """Signals that may run: DSL closure + always_run_audit."""
    graph = build_dependency_graph(signals_by_name)
    dsl_roots = extract_dsl_identifiers(dsl_expression) & set(signals_by_name.keys())
    needed = _closure_from_roots(dsl_roots, graph)

    for name, sig in signals_by_name.items():
        role = getattr(sig, "execution_role", EXECUTION_ROLE_REFERENCED)
        if role == EXECUTION_ROLE_ALWAYS_AUDIT:
            needed.add(name)
            needed |= _closure_from_roots(signal_dependency_names(sig) & set(signals_by_name.keys()), graph)
        elif role == EXECUTION_ROLE_MANUAL_TEST and include_manual_test:
            needed.add(name)
            needed |= _closure_from_roots(signal_dependency_names(sig) & set(signals_by_name.keys()), graph)

    return needed


def topological_execution_order(
    signal_names: Set[str],
    graph: Mapping[str, Set[str]],
    signals_by_name: Mapping[str, Any],
) -> List[str]:
    """Dependency-respecting order, then stage / criticality / priority / cost / name."""
    sub_graph = {n: graph.get(n, set()) & signal_names for n in signal_names}
    in_degree = {n: 0 for n in signal_names}
    for node, deps in sub_graph.items():
        for dep in deps:
            if dep in signal_names:
                in_degree[node] += 1

    ready = [n for n in signal_names if in_degree[n] == 0]
    ordered: List[str] = []
    while ready:
        ready.sort(key=lambda n: _sort_key(signals_by_name[n]))
        current = ready.pop(0)
        ordered.append(current)
        for node, deps in sub_graph.items():
            if current in deps:
                in_degree[node] -= 1
                if in_degree[node] == 0:
                    ready.append(node)
    for node in signal_names:
        if node not in ordered:
            ordered.append(node)
    return ordered


def _sort_key(signal: Any) -> tuple:
    stage = getattr(signal, "effective_stage", signal.order_of_evaluation)
    crit = CRITICALITY_ORDER.get(getattr(signal, "criticality", "preferred"), 1)
    priority = getattr(signal, "effective_priority", getattr(signal, "default_priority", 500))
    cost = getattr(signal, "cost", 0)
    return (stage, crit, priority, cost, signal.name)


def partition_by_budget(
    candidates: List[Any],
    spent: int,
    max_cost: Optional[int],
    budget_override: bool,
) -> Tuple[List[Any], List[Any]]:
    if budget_override or max_cost is None:
        return candidates, []
    runnable: List[Any] = []
    skipped: List[Any] = []
    budget = spent
    for sig in candidates:
        est = getattr(sig, "cost", 0)
        if budget + est > max_cost:
            skipped.append(sig)
        else:
            runnable.append(sig)
            budget += est
    return runnable, skipped


def dependencies_satisfied(signal: Any, produced: Mapping[str, Any]) -> bool:
    deps = signal_dependency_names(signal)
    signal_names_in_deps = deps  # placeholders may be request params — caller filters
    for dep in deps:
        if dep in produced:
            continue
        # request params handled by executor; only signal-signal deps here
        if dep not in produced:
            # If it's a signal name we track, it's missing
            return False
    return True


def missing_signal_dependencies(signal: Any, produced: Mapping[str, Any], all_signal_names: Set[str]) -> List[str]:
    missing = []
    for dep in signal_dependency_names(signal):
        if dep in all_signal_names and dep not in produced:
            missing.append(dep)
    return missing


def coerce_terminal_decline(signal_name: str, value: Any) -> bool:
    if value in (True, "True", "true", 1):
        return True
    if value in (False, "False", "false", 0, None, ""):
        return False
    try:
        return bool(value)
    except Exception:
        return False


def should_skip_expensive_after_decline(signal: Any, terminal_decline: bool) -> bool:
    if not terminal_decline:
        return False
    if getattr(signal, "vendor_audit_after_decline", False):
        return False
    if getattr(signal, "is_expensive_vendor", False):
        return True
    if getattr(signal, "type", None) == "external_endpoint" and getattr(signal, "cost", 0) > 0:
        return True
    return False


def compute_actual_cost(signal: Any, *, success: bool, attempt_started: bool, cache_hit: bool) -> int:
    if cache_hit:
        return 0
    billable = getattr(signal, "billable_event", "success")
    if billable == "never":
        return 0
    if billable == "attempt":
        return getattr(signal, "cost", 0) if attempt_started else 0
    return getattr(signal, "cost", 0) if success else 0


def resolve_outcome(
    *,
    dsl_expression: str,
    produced: Mapping[str, Any],
    records: Mapping[str, SignalExecutionRecord],
    dsl_required_names: Set[str],
    budget_exceeded_policy: str,
    vendor_failure_policy: str,
    checkpoint_timed_out: bool,
    engine_error: bool,
) -> OutcomeResolution:
    if engine_error:
        return OutcomeResolution(DecisionOutcome.ERROR, "engine_error")

    if checkpoint_timed_out:
        return OutcomeResolution(DecisionOutcome.INCOMPLETE, "checkpoint_timeout")

    for rec in records.values():
        if rec.status == ExecutionStatus.SKIPPED_BUDGET and rec.criticality == "required":
            if budget_exceeded_policy == "fail_closed":
                return OutcomeResolution(DecisionOutcome.DECLINE, "budget_required_signal_skipped")
            return OutcomeResolution(DecisionOutcome.REFER, "budget_required_signal_skipped")
        if rec.status == ExecutionStatus.FAILED and rec.criticality == "required":
            if vendor_failure_policy == "fail_closed":
                return OutcomeResolution(DecisionOutcome.DECLINE, "required_vendor_failed")
            if vendor_failure_policy == "error":
                return OutcomeResolution(DecisionOutcome.ERROR, "required_vendor_failed")
            return OutcomeResolution(DecisionOutcome.REFER, "required_vendor_failed")

    for name in dsl_required_names:
        rec = records.get(name)
        if rec is None:
            return OutcomeResolution(DecisionOutcome.INCOMPLETE, "required_dependency_not_produced")
        if rec.status in (
            ExecutionStatus.SKIPPED_DEPENDENCY,
            ExecutionStatus.NOT_EVALUATED,
        ) and rec.criticality == "required":
            return OutcomeResolution(DecisionOutcome.INCOMPLETE, "required_dependency_not_produced")

    eval_context = {k: v for k, v in produced.items()}
    missing_for_dsl = [n for n in dsl_required_names if n not in eval_context]
    if missing_for_dsl:
        return OutcomeResolution(DecisionOutcome.INCOMPLETE, "required_dependency_not_produced")

    try:
        policy_pass = bool(evaluate_expression(dsl_expression, eval_context))
    except Exception:
        return OutcomeResolution(DecisionOutcome.INCOMPLETE, "policy_not_evaluable")

    degraded = False
    for rec in records.values():
        if rec.criticality in ("preferred", "optional") and rec.status in (
            ExecutionStatus.FAILED,
            ExecutionStatus.SKIPPED_BUDGET,
            ExecutionStatus.SKIPPED_CONDITION,
            ExecutionStatus.SKIPPED_DEPENDENCY,
        ):
            degraded = True

    if policy_pass:
        return OutcomeResolution(
            DecisionOutcome.APPROVE,
            "policy_pass",
            degraded=degraded,
        )
    return OutcomeResolution(DecisionOutcome.DECLINE, "policy_fail")


def build_execution_plan(
    *,
    dsl_expression: str,
    signals: List[Any],
    include_manual_test: bool,
) -> Tuple[List[str], Set[str], Dict[str, Set[str]]]:
    signals_by_name = {s.name: s for s in signals}
    graph = build_dependency_graph(signals_by_name)
    execution_set = compute_execution_set(
        dsl_expression=dsl_expression,
        signals_by_name=signals_by_name,
        include_manual_test=include_manual_test,
    )
    ordered = topological_execution_order(execution_set, graph, signals_by_name)
    return ordered, execution_set, graph


def group_parallel_batches(ordered_names: List[str], signals_by_name: Mapping[str, Any]) -> List[List[str]]:
    """Group consecutive same-stage signals that allow parallel into batches."""
    batches: List[List[str]] = []
    current_stage: Optional[int] = None
    parallel_group: List[str] = []

    def flush_serial(name: str) -> None:
        nonlocal parallel_group, current_stage
        if parallel_group:
            batches.append(parallel_group)
            parallel_group = []
        batches.append([name])
        current_stage = None

    for name in ordered_names:
        sig = signals_by_name[name]
        stage = getattr(sig, "effective_stage", sig.order_of_evaluation)
        if sig.can_run_in_parallel:
            if parallel_group and stage == current_stage:
                parallel_group.append(name)
            else:
                if parallel_group:
                    batches.append(parallel_group)
                parallel_group = [name]
                current_stage = stage
        else:
            if parallel_group:
                batches.append(parallel_group)
                parallel_group = []
            batches.append([name])
            current_stage = None
    if parallel_group:
        batches.append(parallel_group)
    return batches
