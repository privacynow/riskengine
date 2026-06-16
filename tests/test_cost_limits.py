from engine.services.decision import partition_signals_by_cost
from engine.services.tenancy import ExecutableSignalRow


def _signal(name: str, cost: int, order: int = 1) -> ExecutableSignalRow:
    return ExecutableSignalRow(
        id=f"id-{name}",
        name=name,
        type="expression",
        method_of_call=None,
        expression_body="True",
        cost=cost,
        cache_expiration_seconds=0,
        timeout_seconds=30,
        can_run_in_parallel=False,
        order_of_evaluation=order,
        http_method=None,
        request_url_params_template=None,
        request_body_template=None,
        request_headers_template=None,
        bearer_token=None,
        allow_caching=False,
        global_reuse=False,
        function_params_template=None,
    )


class TestCostPartitioning:
    def test_reserves_budget_sequentially_within_group(self):
        group = [_signal("a", 40), _signal("b", 40), _signal("c", 40)]
        runnable, skipped = partition_signals_by_cost(group, total_cost=30, max_cost=100, override_cost_flag=False)
        assert [s.name for s in runnable] == ["a"]
        assert [s.name for s in skipped] == ["b", "c"]

    def test_override_cost_flag_runs_all(self):
        group = [_signal("a", 90), _signal("b", 90)]
        runnable, skipped = partition_signals_by_cost(group, total_cost=0, max_cost=50, override_cost_flag=True)
        assert [s.name for s in runnable] == ["a", "b"]
        assert skipped == []

    def test_prior_order_cost_reduces_remaining_budget(self):
        group = [_signal("late", 60)]
        runnable, skipped = partition_signals_by_cost(
            group, total_cost=50, max_cost=100, override_cost_flag=False
        )
        assert runnable == []
        assert [s.name for s in skipped] == ["late"]
