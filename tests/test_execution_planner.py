import pytest

from engine.services.execution_planner import (
    DependencyCycleError,
    build_execution_plan,
    compute_execution_set,
    resolve_outcome,
    ExecutionStatus,
    SignalExecutionRecord,
)
from engine.services.tenancy import ExecutableSignalRow


def _row(name: str, *, expr: str = "True", cost: int = 0, criticality: str = "preferred", role: str = "referenced_policy", stage: int = 1, expensive: bool = False):
    return ExecutableSignalRow(
        id=f"id-{name}",
        name=name,
        type="expression",
        method_of_call=None,
        expression_body=expr,
        cost=cost,
        cache_expiration_seconds=0,
        timeout_seconds=30,
        can_run_in_parallel=False,
        order_of_evaluation=stage,
        http_method=None,
        request_url_params_template=None,
        request_body_template=None,
        request_headers_template=None,
        bearer_token=None,
        allow_caching=False,
        global_reuse=False,
        function_params_template=None,
        effective_stage=stage,
        criticality=criticality,
        execution_role=role,
        is_expensive_vendor=expensive,
    )


class TestExecutionPlanner:
    def test_dependency_closure_includes_expression_deps(self):
        signals = [
            _row("credit_score", cost=30, expensive=True),
            _row("credit_pass", expr="credit_score >= 680"),
        ]
        by_name = {s.name: s for s in signals}
        needed = compute_execution_set(
            dsl_expression="credit_pass",
            signals_by_name=by_name,
            include_manual_test=False,
        )
        assert needed == {"credit_score", "credit_pass"}

    def test_unreferenced_linked_signal_excluded(self):
        signals = [
            _row("age_check"),
            _row("unused_audit", role="referenced_policy"),
        ]
        by_name = {s.name: s for s in signals}
        needed = compute_execution_set(
            dsl_expression="age_check",
            signals_by_name=by_name,
            include_manual_test=False,
        )
        assert needed == {"age_check"}

    def test_budget_skip_required_is_refer(self):
        records = {
            "credit_score": SignalExecutionRecord(
                name="credit_score",
                signal_id="1",
                status=ExecutionStatus.SKIPPED_BUDGET,
                criticality="required",
            )
        }
        outcome = resolve_outcome(
            dsl_expression="credit_score >= 680",
            produced={},
            records=records,
            dsl_required_names={"credit_score"},
            budget_exceeded_policy="refer",
            vendor_failure_policy="refer",
            checkpoint_timed_out=False,
            engine_error=False,
        )
        assert outcome.outcome.value == "REFER"
        assert outcome.reason == "budget_required_signal_skipped"

    def test_missing_dependency_is_incomplete(self):
        outcome = resolve_outcome(
            dsl_expression="credit_pass",
            produced={},
            records={},
            dsl_required_names={"credit_pass"},
            budget_exceeded_policy="refer",
            vendor_failure_policy="refer",
            checkpoint_timed_out=False,
            engine_error=False,
        )
        assert outcome.outcome.value == "INCOMPLETE"

    def test_degraded_approve_when_optional_missing(self):
        records = {
            "age_check": SignalExecutionRecord(
                name="age_check",
                signal_id="1",
                status=ExecutionStatus.RAN,
                criticality="required",
            ),
            "extra": SignalExecutionRecord(
                name="extra",
                signal_id="2",
                status=ExecutionStatus.SKIPPED_CONDITION,
                criticality="optional",
            ),
        }
        outcome = resolve_outcome(
            dsl_expression="age_check",
            produced={"age_check": True},
            records=records,
            dsl_required_names={"age_check"},
            budget_exceeded_policy="refer",
            vendor_failure_policy="refer",
            checkpoint_timed_out=False,
            engine_error=False,
        )
        assert outcome.outcome.value == "APPROVE"
        assert outcome.degraded is True

    def test_dependency_cycle_raises(self):
        with pytest.raises(DependencyCycleError):
            build_execution_plan(
                dsl_expression="a",
                signals=[_row("a", expr="b"), _row("b", expr="a")],
                include_manual_test=False,
            )
