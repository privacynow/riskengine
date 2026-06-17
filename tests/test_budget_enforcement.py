import asyncio

import pytest

from engine.models import DecisionRequest
from engine.services.budget_tracker import BudgetTracker, admit_signals_under_budget
from engine.services.decision import execute_decision
from engine.services.execution_planner import DependencyCycleError, build_execution_plan
from engine.services.tenancy import ExecutableSignalRow
from tests.conftest import SAMPLE_TENANT
from tests.test_decision_orchestration import (
    SAMPLE_ONBOARDING_CHECKPOINT,
    _checkpoint_row,
    _execution_context,
    _expression_signal,
)


class TestBudgetTracker:
    def test_parallel_admission_does_not_overspend_checkpoint_cap(self):
        tracker = BudgetTracker(checkpoint_cap=100, tenant_limit=None, tenant_used=0)
        signals = [
            _expression_signal("a", cost=80, parallel=True),
            _expression_signal("b", cost=80, parallel=True),
        ]
        admitted, rejected = admit_signals_under_budget(signals, tracker)
        assert [s.name for s in admitted] == ["a"]
        assert [s.name for s in rejected] == ["b"]

    def test_tenant_reserve_is_cumulative_within_decision(self):
        tracker = BudgetTracker(checkpoint_cap=None, tenant_limit=100, tenant_used=50)
        assert tracker.try_reserve(40) is True
        assert tracker.try_reserve(20) is False
        assert tracker.try_reserve(10) is True

    def test_total_reserved_survives_commit(self):
        tracker = BudgetTracker(checkpoint_cap=100, tenant_limit=None, tenant_used=0)
        assert tracker.try_reserve(30) is True
        tracker.commit_actual(reserved_units=30, actual_units=25)
        assert tracker.checkpoint_reserved == 0
        assert tracker.checkpoint_total_reserved == 30
        assert tracker.checkpoint_actual == 25


class TestDependencyCycles:
    def test_cycle_raises(self):
        from engine.services.execution_planner import DependencyCycleError, build_execution_plan

        a = _expression_signal("a", expression_body="b")
        b = _expression_signal("b", expression_body="a")
        with pytest.raises(DependencyCycleError):
            build_execution_plan(
                dsl_expression="a",
                signals=[a, b],
                include_manual_test=False,
            )


@pytest.mark.skipif(
    not __import__("os").environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres",
)
class TestBudgetOverrideAudit:
    def test_override_requires_reason(self):
        from fastapi.testclient import TestClient

        from engine.main import app
        from tests.conftest import TEST_ADMIN_TOKEN

        client = TestClient(app)
        resp = client.post(
            "/ui/test_decisions",
            headers={"Authorization": f"Bearer {TEST_ADMIN_TOKEN}"},
            json={
                "tenant_id": SAMPLE_TENANT,
                "checkpoint_name": "Onboarding",
                "budgetOverride": True,
            },
        )
        assert resp.status_code == 422


class TestParallelBudgetExecution:
    @pytest.fixture(autouse=True)
    def noop_persist(self, monkeypatch):
        from engine.services import decision as decision_mod

        def _noop_persist(conn, cur, **kwargs):
            conn.commit()
            return kwargs.get("decision_outcome", "APPROVE"), kwargs.get("decision_reason", "policy_pass")

        monkeypatch.setattr(decision_mod, "persist_decision_outcome", _noop_persist)

    def test_parallel_batch_skips_second_signal_under_cap(self, monkeypatch):
        from engine.services import decision as decision_mod

        async def cheap_invoke(**kwargs):
            return True

        monkeypatch.setattr(decision_mod, "invoke_signal", cheap_invoke)
        monkeypatch.setattr(
            decision_mod,
            "load_decision_execution_context",
            lambda tenant_id, request, checkpoint_id=None: _execution_context(
                [
                    _expression_signal("parallel_a", cost=80, parallel=True),
                    _expression_signal("parallel_b", cost=80, parallel=True),
                ],
                id=checkpoint_id or SAMPLE_ONBOARDING_CHECKPOINT,
                tenant_id=tenant_id,
                name="parallel-budget-test",
                dsl_expression="parallel_a and parallel_b",
                max_cost=100,
            ),
        )

        response = asyncio.run(
            execute_decision(
                SAMPLE_TENANT,
                DecisionRequest(checkpoint_name="parallel-budget-test", applicant_id="app-1"),
                checkpoint_id=SAMPLE_ONBOARDING_CHECKPOINT,
            )
        )

        statuses = {item.name: item.status for item in response.signals}
        assert statuses["parallel_a"] == "ran"
        assert statuses["parallel_b"] == "skipped_budget"
        assert response.cost.reserved_units >= 80


@pytest.mark.skipif(
    not __import__("os").environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres",
)
class TestTenantBudgetDbLease:
    def test_atomic_lease_blocks_overspend(self):
        from engine.db import db_cursor
        from engine.services.tenant_budget import (
            finalize_tenant_budget_signal,
            lease_tenant_budget_units,
            load_tenant_budget,
        )

        with db_cursor() as (conn, cur):
            cur.execute(
                """
                UPDATE tenant_budgets
                   SET used_units = 0, reserved_units = 0, limit_units = 100
                 WHERE tenant_id = %s
                """,
                (SAMPLE_TENANT,),
            )
            conn.commit()

        assert lease_tenant_budget_units(SAMPLE_TENANT, 60) is True
        assert lease_tenant_budget_units(SAMPLE_TENANT, 50) is False
        finalize_tenant_budget_signal(SAMPLE_TENANT, 60, 40)
        budget = load_tenant_budget(SAMPLE_TENANT)
        assert budget is not None
        assert budget.used_units == 40
        assert budget.reserved_units == 0
        assert budget.remaining_units == 60
