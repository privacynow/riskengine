import os
import uuid

import pytest

from engine.db import db_cursor
from engine.services.tenancy import (
    fetch_current_checkpoint_row,
    fetch_current_signal_row,
    fetch_executable_signal_rows,
)


SAMPLE_TENANT = "11111111-1111-1111-1111-111111111111"
ONBOARDING_CP = "22222222-2222-2222-2222-222222222201"


@pytest.mark.skipif(
    os.environ.get("DB_HOST", "localhost") == "localhost"
    and not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres",
)
class TestTenancyIntegration:
    def test_current_checkpoint_resolution(self):
        with db_cursor() as (_, cur):
            row = fetch_current_checkpoint_row(cur, SAMPLE_TENANT, "Onboarding")
            assert row.id == ONBOARDING_CP
            assert row.name == "Onboarding"

    def test_current_signal_resolution_strict(self):
        with db_cursor() as (_, cur):
            row = fetch_current_signal_row(cur, SAMPLE_TENANT, "age_check")
            assert row.name == "age_check"

    def test_inactive_linked_signal_skipped(self):
        with db_cursor() as (_, cur):
            signals = fetch_executable_signal_rows(cur, SAMPLE_TENANT, ONBOARDING_CP)
            names = {s.name for s in signals}
            assert "inactive_demo" not in names
            assert "age_check" in names

    def test_executable_signals_dedupe_logical_name(self):
        stale_id = str(uuid.uuid4())
        link_id = str(uuid.uuid4())
        with db_cursor() as (conn, cur):
            current = fetch_current_signal_row(cur, SAMPLE_TENANT, "age_check")
            cur.execute(
                """
                INSERT INTO signals (
                    id, tenant_id, name, description, type, method_of_call, expression_body,
                    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
                    order_of_evaluation, http_method, request_url_params_template,
                    request_body_template, request_headers_template, bearer_token,
                    allow_caching, global_reuse, function_params_template
                )
                SELECT
                    %s, tenant_id, name, description, type, method_of_call, expression_body,
                    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
                    order_of_evaluation, http_method, request_url_params_template,
                    request_body_template, request_headers_template, bearer_token,
                    allow_caching, global_reuse, function_params_template
                  FROM signals
                 WHERE id = %s
                """,
                (stale_id, current.id),
            )
            cur.execute(
                """
                INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
                VALUES (%s, %s, %s)
                """,
                (link_id, ONBOARDING_CP, stale_id),
            )
            conn.commit()

            signals = fetch_executable_signal_rows(cur, SAMPLE_TENANT, ONBOARDING_CP)
            age_checks = [signal for signal in signals if signal.name == "age_check"]
            assert len(age_checks) == 1
            assert age_checks[0].id == current.id

            cur.execute("DELETE FROM checkpoint_signals WHERE id = %s", (link_id,))
            cur.execute("DELETE FROM signals WHERE id = %s", (stale_id,))
            conn.commit()

    def test_executable_signals_preserve_evaluation_order_after_dedupe(self):
        checkpoint_id = str(uuid.uuid4())
        first_signal_id = str(uuid.uuid4())
        second_signal_id = str(uuid.uuid4())
        link_first = str(uuid.uuid4())
        link_second = str(uuid.uuid4())
        first_name = f"z_order_first_{uuid.uuid4().hex[:8]}"
        second_name = f"a_order_second_{uuid.uuid4().hex[:8]}"
        with db_cursor() as (conn, cur):
            try:
                cur.execute(
                    """
                    INSERT INTO checkpoints (
                        id, tenant_id, name, description, type, dsl_expression,
                        method_of_call, max_cost, override_cost_flag, timeout_seconds
                    )
                    VALUES (%s, %s, %s, NULL, 'onboarding', 'True', NULL, 10, TRUE, 30)
                    """,
                    (checkpoint_id, SAMPLE_TENANT, f"order-test-{uuid.uuid4().hex[:8]}"),
                )
                for signal_id, name, order in [
                    (first_signal_id, first_name, 1),
                    (second_signal_id, second_name, 2),
                ]:
                    cur.execute(
                        """
                        INSERT INTO signals (
                            id, tenant_id, name, description, type, method_of_call, expression_body,
                            cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
                            order_of_evaluation, http_method, request_url_params_template,
                            request_body_template, request_headers_template, bearer_token,
                            allow_caching, global_reuse, function_params_template
                        )
                        VALUES (
                            %s, %s, %s, NULL, 'expression', NULL, 'True',
                            0, 0, 30, FALSE, %s, NULL, NULL, NULL, NULL, NULL,
                            FALSE, FALSE, NULL
                        )
                        """,
                        (signal_id, SAMPLE_TENANT, name, order),
                    )
                    cur.execute(
                        """
                        INSERT INTO signal_current_version (tenant_id, name, signal_id)
                        VALUES (%s, %s, %s)
                        """,
                        (SAMPLE_TENANT, name, signal_id),
                    )
                cur.execute(
                    """
                    INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
                    VALUES (%s, %s, %s), (%s, %s, %s)
                    """,
                    (
                        link_first,
                        checkpoint_id,
                        first_signal_id,
                        link_second,
                        checkpoint_id,
                        second_signal_id,
                    ),
                )
                conn.commit()

                signals = fetch_executable_signal_rows(cur, SAMPLE_TENANT, checkpoint_id)
                assert [signal.name for signal in signals] == [first_name, second_name]
            finally:
                cur.execute(
                    "DELETE FROM checkpoint_signals WHERE id = ANY(%s::uuid[])",
                    ([link_first, link_second],),
                )
                cur.execute(
                    "DELETE FROM signal_current_version WHERE signal_id = ANY(%s::uuid[])",
                    ([first_signal_id, second_signal_id],),
                )
                cur.execute(
                    "DELETE FROM signals WHERE id = ANY(%s::uuid[])",
                    ([first_signal_id, second_signal_id],),
                )
                cur.execute("DELETE FROM checkpoints WHERE id = %s", (checkpoint_id,))
                conn.commit()
