import asyncio
import os
import uuid

import pytest

from engine.models import DecisionRequest
from engine.services.decision import execute_decision
from engine.services.tenancy import ExecutableSignalRow
from tests.conftest import SAMPLE_TENANT

SAMPLE_ONBOARDING_CHECKPOINT = "22222222-2222-2222-2222-222222222201"


def _expression_signal(
    name: str,
    *,
    order: int = 1,
    parallel: bool = False,
    timeout_seconds: int = 30,
    expression_body: str = "True",
    cost: int = 1,
) -> ExecutableSignalRow:
    return ExecutableSignalRow(
        id=str(uuid.uuid5(uuid.NAMESPACE_OID, f"test-signal-{name}")),
        name=name,
        type="expression",
        method_of_call=None,
        expression_body=expression_body,
        cost=cost,
        cache_expiration_seconds=0,
        timeout_seconds=timeout_seconds,
        can_run_in_parallel=parallel,
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


@pytest.mark.skipif(
    os.environ.get("DB_HOST", "localhost") == "localhost"
    and not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres (set DB_HOST or RUN_INTEGRATION_TESTS=1)",
)
class TestDecisionOrchestration:
    @pytest.fixture(autouse=True)
    def noop_signal_log_persist(self, monkeypatch):
        from engine.services import decision as decision_mod

        monkeypatch.setattr(decision_mod, "persist_signal_logs", lambda cur, items: None)

    def test_expression_signal_receives_request_params(self, monkeypatch):
        from engine.db import get_db_connection
        from engine.services import decision as decision_mod

        captured: dict = {}

        async def fake_invoke(*, invoke_context, expression_body, **kwargs):
            captured["context"] = dict(invoke_context)
            captured["expression_body"] = expression_body
            return invoke_context.get("request_score", 0) > 10

        monkeypatch.setattr(decision_mod, "invoke_signal", fake_invoke)
        monkeypatch.setattr(
            decision_mod,
            "fetch_executable_signal_rows",
            lambda cur, tenant_id, checkpoint_id: [
                _expression_signal("score_gate", expression_body="request_score > 10")
            ],
        )

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            from engine.services.tenancy import CheckpointRow

            monkeypatch.setattr(
                decision_mod,
                "fetch_checkpoint_row_by_id",
                lambda cur, tenant_id, checkpoint_id: CheckpointRow(
                    id=checkpoint_id,
                    tenant_id=tenant_id,
                    name="orch-test",
                    description=None,
                    type="onboarding",
                    dsl_expression="score_gate",
                    method_of_call=None,
                    max_cost=10,
                    override_cost_flag=True,
                    timeout_seconds=30,
                ),
            )

            response = asyncio.run(
                execute_decision(
                    conn,
                    cur,
                    SAMPLE_TENANT,
                    DecisionRequest(
                        checkpoint_name="orch-test",
                        applicant_id="app-1",
                        parameters={"request_score": 12},
                    ),
                    checkpoint_id=SAMPLE_ONBOARDING_CHECKPOINT,
                )
            )
        finally:
            cur.close()
            conn.close()

        assert captured["context"]["request_score"] == 12
        assert response.signal_results["score_gate"] is True

    def test_checkpoint_deadline_caps_signal_wait(self, monkeypatch):
        from engine.db import get_db_connection
        from engine.services import decision as decision_mod

        async def slow_invoke(**kwargs):
            await asyncio.sleep(2)
            return True

        monkeypatch.setattr(decision_mod, "invoke_signal", slow_invoke)
        monkeypatch.setattr(
            decision_mod,
            "fetch_executable_signal_rows",
            lambda cur, tenant_id, checkpoint_id: [
                _expression_signal("slow_signal", timeout_seconds=30)
            ],
        )

        from engine.services.tenancy import CheckpointRow

        monkeypatch.setattr(
            decision_mod,
            "fetch_checkpoint_row_by_id",
            lambda cur, tenant_id, checkpoint_id: CheckpointRow(
                id=checkpoint_id,
                tenant_id=tenant_id,
                name="deadline-test",
                description=None,
                type="onboarding",
                dsl_expression="slow_signal",
                method_of_call=None,
                max_cost=10,
                override_cost_flag=True,
                timeout_seconds=1,
            ),
        )

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            response = asyncio.run(
                execute_decision(
                    conn,
                    cur,
                    SAMPLE_TENANT,
                    DecisionRequest(checkpoint_name="deadline-test", applicant_id="app-1"),
                    checkpoint_id=SAMPLE_ONBOARDING_CHECKPOINT,
                )
            )
        finally:
            cur.close()
            conn.close()

        assert response.signal_results["slow_signal"] is False
        assert response.final_decision_value == "False"

    def test_parallel_batch_runs_concurrently(self, monkeypatch):
        from engine.db import get_db_connection
        from engine.services import decision as decision_mod

        started: list[str] = []

        async def track_invoke(*, expression_body, **kwargs):
            started.append("start")
            await asyncio.sleep(0.2)
            started.append("end")
            return True

        monkeypatch.setattr(decision_mod, "invoke_signal", track_invoke)
        monkeypatch.setattr(
            decision_mod,
            "fetch_executable_signal_rows",
            lambda cur, tenant_id, checkpoint_id: [
                _expression_signal("parallel_a", parallel=True),
                _expression_signal("parallel_b", parallel=True),
            ],
        )

        from engine.services.tenancy import CheckpointRow

        monkeypatch.setattr(
            decision_mod,
            "fetch_checkpoint_row_by_id",
            lambda cur, tenant_id, checkpoint_id: CheckpointRow(
                id=checkpoint_id,
                tenant_id=tenant_id,
                name="parallel-test",
                description=None,
                type="onboarding",
                dsl_expression="parallel_a and parallel_b",
                method_of_call=None,
                max_cost=10,
                override_cost_flag=True,
                timeout_seconds=30,
            ),
        )

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            asyncio.run(
                execute_decision(
                    conn,
                    cur,
                    SAMPLE_TENANT,
                    DecisionRequest(checkpoint_name="parallel-test", applicant_id="app-1"),
                    checkpoint_id=SAMPLE_ONBOARDING_CHECKPOINT,
                )
            )
        finally:
            cur.close()
            conn.close()

        assert started[:2] == ["start", "start"]

    def test_cost_skip_writes_terminal_signal_audit(self, monkeypatch):
        from engine.db import get_db_connection
        from engine.services import decision as decision_mod

        captured: list[dict] = []

        def capture_persist(cur, items):
            captured.extend(items)

        monkeypatch.setattr(decision_mod, "persist_signal_logs", capture_persist)
        monkeypatch.setattr(
            decision_mod,
            "fetch_executable_signal_rows",
            lambda cur, tenant_id, checkpoint_id: [
                _expression_signal("cheap_signal", cost=1),
                _expression_signal("expensive_signal", cost=50, order=2),
            ],
        )

        from engine.services.tenancy import CheckpointRow

        monkeypatch.setattr(
            decision_mod,
            "fetch_checkpoint_row_by_id",
            lambda cur, tenant_id, checkpoint_id: CheckpointRow(
                id=checkpoint_id,
                tenant_id=tenant_id,
                name="cost-skip-test",
                description=None,
                type="onboarding",
                dsl_expression="cheap_signal and expensive_signal",
                method_of_call=None,
                max_cost=1,
                override_cost_flag=False,
                timeout_seconds=30,
            ),
        )

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            asyncio.run(
                execute_decision(
                    conn,
                    cur,
                    SAMPLE_TENANT,
                    DecisionRequest(checkpoint_name="cost-skip-test", applicant_id="app-1"),
                    checkpoint_id=SAMPLE_ONBOARDING_CHECKPOINT,
                )
            )
        finally:
            cur.close()
            conn.close()

        skipped = [item for item in captured if item.get("error_message") == "cost_budget_exceeded"]
        assert skipped
        assert skipped[0]["success"] is False

    def test_parallel_checkpoint_timeout_preserves_completed_results(self, monkeypatch):
        from engine.db import get_db_connection
        from engine.services import decision as decision_mod

        captured: list[dict] = []

        def capture_persist(cur, items):
            captured.extend(items)

        async def fake_invoke(*, expression_body, **kwargs):
            if expression_body == "slow":
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(0.05)
            return True

        monkeypatch.setattr(decision_mod, "persist_signal_logs", capture_persist)
        monkeypatch.setattr(decision_mod, "invoke_signal", fake_invoke)
        monkeypatch.setattr(
            decision_mod,
            "fetch_executable_signal_rows",
            lambda cur, tenant_id, checkpoint_id: [
                _expression_signal(
                    "fast_signal",
                    parallel=True,
                    expression_body="fast",
                    timeout_seconds=30,
                ),
                _expression_signal(
                    "slow_signal",
                    parallel=True,
                    expression_body="slow",
                    timeout_seconds=30,
                ),
            ],
        )

        from engine.services.tenancy import CheckpointRow

        monkeypatch.setattr(
            decision_mod,
            "fetch_checkpoint_row_by_id",
            lambda cur, tenant_id, checkpoint_id: CheckpointRow(
                id=checkpoint_id,
                tenant_id=tenant_id,
                name="partial-timeout-test",
                description=None,
                type="onboarding",
                dsl_expression="fast_signal and slow_signal",
                method_of_call=None,
                max_cost=10,
                override_cost_flag=True,
                timeout_seconds=1,
            ),
        )

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            response = asyncio.run(
                execute_decision(
                    conn,
                    cur,
                    SAMPLE_TENANT,
                    DecisionRequest(
                        checkpoint_name="partial-timeout-test",
                        applicant_id="app-1",
                    ),
                    checkpoint_id=SAMPLE_ONBOARDING_CHECKPOINT,
                )
            )
        finally:
            cur.close()
            conn.close()

        assert response.signal_results["fast_signal"] is True
        assert response.signal_results["slow_signal"] is False
        timeout_logs = [
            item for item in captured if item.get("error_message") == "checkpoint_timeout"
        ]
        slow_id = str(uuid.uuid5(uuid.NAMESPACE_OID, "test-signal-slow_signal"))
        assert [item["signal_id"] for item in timeout_logs] == [slow_id]


@pytest.mark.skipif(
    os.environ.get("DB_HOST", "localhost") == "localhost"
    and not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres (set DB_HOST or RUN_INTEGRATION_TESTS=1)",
)
class TestDecisionAuditDurability:
    def test_completed_decision_persists_atomically_without_pending_row(self, monkeypatch):
        from engine.db import get_db_connection
        from engine.services import decision as decision_mod
        from engine.services.tenancy import CheckpointRow

        async def true_invoke(**kwargs):
            return True

        monkeypatch.setattr(decision_mod, "invoke_signal", true_invoke)
        from dataclasses import replace

        monkeypatch.setattr(
            decision_mod,
            "fetch_executable_signal_rows",
            lambda cur, tenant_id, checkpoint_id: [
                replace(
                    _expression_signal("age_check", expression_body="True"),
                    id="33333333-3333-3333-3333-333333333301",
                )
            ],
        )
        monkeypatch.setattr(
            decision_mod,
            "fetch_checkpoint_row_by_id",
            lambda cur, tenant_id, checkpoint_id: CheckpointRow(
                id=checkpoint_id,
                tenant_id=tenant_id,
                name="audit-durability-test",
                description=None,
                type="onboarding",
                dsl_expression="age_check",
                method_of_call=None,
                max_cost=10,
                override_cost_flag=True,
                timeout_seconds=30,
            ),
        )

        conn = get_db_connection()
        cur = conn.cursor()
        response = None
        try:
            response = asyncio.run(
                execute_decision(
                    conn,
                    cur,
                    SAMPLE_TENANT,
                    DecisionRequest(
                        checkpoint_name="audit-durability-test",
                        applicant_id="audit-durability-applicant",
                    ),
                    checkpoint_id=SAMPLE_ONBOARDING_CHECKPOINT,
                )
            )
            cur.execute(
                """
                SELECT final_decision_value
                  FROM decision_log
                 WHERE id = %s
                """,
                (response.decision_id,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] != "PENDING"
            assert row[0] == response.final_decision_value
            cur.execute(
                """
                SELECT COUNT(*)
                  FROM signal_log
                 WHERE decision_log_id = %s
                """,
                (response.decision_id,),
            )
            assert cur.fetchone()[0] >= 1
        finally:
            if response is not None:
                cur.execute("DELETE FROM signal_log WHERE decision_log_id = %s", (response.decision_id,))
                cur.execute("DELETE FROM decision_log WHERE id = %s", (response.decision_id,))
                conn.commit()
            cur.close()
            conn.close()

    def test_caching_signal_does_not_commit_pending_before_finalize(self, monkeypatch):
        from dataclasses import replace

        from engine.cache import in_memory_signal_cache
        from engine.db import get_db_connection
        from engine.services import decision as decision_mod
        from engine.services.tenancy import CheckpointRow

        signal_id = "33333333-3333-3333-3333-333333333301"

        async def true_invoke(**kwargs):
            return True

        monkeypatch.setattr(decision_mod, "invoke_signal", true_invoke)
        monkeypatch.setattr(
            decision_mod,
            "fetch_executable_signal_rows",
            lambda cur, tenant_id, checkpoint_id: [
                replace(
                    _expression_signal("cached_audit_signal", expression_body="True"),
                    id=signal_id,
                    allow_caching=True,
                    cache_expiration_seconds=300,
                )
            ],
        )
        monkeypatch.setattr(
            decision_mod,
            "fetch_checkpoint_row_by_id",
            lambda cur, tenant_id, checkpoint_id: CheckpointRow(
                id=checkpoint_id,
                tenant_id=tenant_id,
                name="audit-durability-cache-test",
                description=None,
                type="onboarding",
                dsl_expression="cached_audit_signal",
                method_of_call=None,
                max_cost=10,
                override_cost_flag=True,
                timeout_seconds=30,
            ),
        )

        def fail_before_finalize(cur, items):
            raise RuntimeError("forced failure before decision finalize")

        monkeypatch.setattr(decision_mod, "persist_signal_logs", fail_before_finalize)

        conn = get_db_connection()
        cur = conn.cursor()
        applicant_id = f"audit-durability-fail-{uuid.uuid4().hex[:8]}"
        try:
            with pytest.raises(RuntimeError, match="forced failure before decision finalize"):
                asyncio.run(
                    execute_decision(
                        conn,
                        cur,
                        SAMPLE_TENANT,
                        DecisionRequest(
                            checkpoint_name="audit-durability-cache-test",
                            applicant_id=applicant_id,
                        ),
                        checkpoint_id=SAMPLE_ONBOARDING_CHECKPOINT,
                    )
                )
            conn.rollback()
            cur.execute(
                """
                SELECT COUNT(*)
                  FROM decision_log
                 WHERE applicant_id = %s
                   AND final_decision_value = 'PENDING'
                """,
                (applicant_id,),
            )
            assert cur.fetchone()[0] == 0
            cur.execute(
                """
                SELECT COUNT(*)
                  FROM signal_cached_values
                 WHERE tenant_id = %s
                   AND checkpoint_id = %s
                   AND signal_id = %s
                   AND applicant_id = %s
                """,
                (
                    SAMPLE_TENANT,
                    SAMPLE_ONBOARDING_CHECKPOINT,
                    signal_id,
                    applicant_id,
                ),
            )
            assert cur.fetchone()[0] == 0
            assert (
                in_memory_signal_cache.get(
                    SAMPLE_TENANT,
                    SAMPLE_ONBOARDING_CHECKPOINT,
                    applicant_id,
                    signal_id,
                )
                is None
            )
        finally:
            cur.close()
            conn.close()
