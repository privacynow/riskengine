import os

import pytest
from fastapi.testclient import TestClient

from tests.conftest import SAMPLE_TENANT, TEST_ADMIN_TOKEN, TEST_SAMPLE_TOKEN


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.skipif(
    os.environ.get("DB_HOST", "localhost") == "localhost"
    and not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres (set DB_HOST or RUN_INTEGRATION_TESTS=1)",
)
class TestAdminHygiene:
    def test_make_current_missing_checkpoint_returns_404_not_500(self, client):
        resp = client.post(
            "/ui/checkpoints/00000000-0000-0000-0000-000000000000/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert resp.status_code == 404

    def test_runtime_checkpoint_omits_template_fields(self, client):
        resp = client.get(
            "/checkpoints/Onboarding",
            headers=auth_header(TEST_SAMPLE_TOKEN),
        )
        assert resp.status_code == 200
        for signal in resp.json()["signals"]:
            assert "request_headers_template" not in signal
            assert "request_body_template" not in signal
            assert "request_url_params_template" not in signal

    def test_admin_signal_list_redacts_header_templates(self, client):
        resp = client.get("/ui/signals?page=1&size=50", headers=auth_header(TEST_ADMIN_TOKEN))
        assert resp.status_code == 200
        for signal in resp.json()["items"]:
            headers = signal.get("request_headers_template") or ""
            assert "Bearer" not in headers or "[REDACTED]" in headers
            assert "bearer_token" not in signal

    def test_copy_tenant_clears_bearer_tokens_and_preserves_links(self, client):
        create = client.post(
            "/ui/tenants",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"name": "COPY TEST TENANT", "copyFromTenantId": SAMPLE_TENANT},
        )
        assert create.status_code == 200
        new_tenant_id = create.json()["id"]

        source_cp = client.get(
            f"/ui/checkpoints?tenant_id={SAMPLE_TENANT}&active_only=true&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        source_onboarding = next(item for item in source_cp if item["name"] == "Onboarding")
        source_links = client.get(
            f"/ui/signals?checkpoint_id={source_onboarding['id']}&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]

        copied_cp = client.get(
            f"/ui/checkpoints?tenant_id={new_tenant_id}&active_only=true&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        copied_onboarding = next(item for item in copied_cp if item["name"] == "Onboarding")

        copied_links = client.get(
            f"/ui/signals?checkpoint_id={copied_onboarding['id']}&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]

        source_names = {s["name"] for s in source_links if s.get("is_current_version")}
        copied_names = {s["name"] for s in copied_links}

        assert copied_names == source_names
        assert len(copied_names) >= 3
        assert all(signal["has_bearer_token"] is False for signal in copied_links)

    def test_copy_tenant_preserves_stale_signal_associations(self, client):
        from db import db_cursor

        old_signal_id = None
        new_signal_id = None
        try:
            with db_cursor() as (conn, cur):
                cur.execute(
                    """
                    SELECT signal_id
                      FROM signal_current_version
                     WHERE tenant_id = %s AND name = 'age_check'
                    """,
                    (SAMPLE_TENANT,),
                )
                row = cur.fetchone()
                assert row is not None
                old_signal_id = str(row[0])

                cur.execute(
                    """
                    INSERT INTO signals (
                        tenant_id, name, description, type, method_of_call,
                        expression_body, cost, cache_expiration_seconds, timeout_seconds,
                        can_run_in_parallel, order_of_evaluation, http_method,
                        request_url_params_template, request_body_template,
                        request_headers_template, bearer_token, allow_caching,
                        global_reuse, function_params_template
                    )
                    SELECT tenant_id, name, description, type, method_of_call,
                           expression_body, cost, cache_expiration_seconds, timeout_seconds,
                           can_run_in_parallel, order_of_evaluation, http_method,
                           request_url_params_template, request_body_template,
                           request_headers_template, NULL, allow_caching,
                           global_reuse, function_params_template
                      FROM signals
                     WHERE id = %s
                    RETURNING id
                    """,
                    (old_signal_id,),
                )
                new_signal_id = str(cur.fetchone()[0])

                cur.execute(
                    """
                    UPDATE signal_current_version
                       SET signal_id = %s, updated_at = NOW()
                     WHERE tenant_id = %s AND name = 'age_check'
                    """,
                    (new_signal_id, SAMPLE_TENANT),
                )
                conn.commit()

            create = client.post(
                "/ui/tenants",
                headers=auth_header(TEST_ADMIN_TOKEN),
                json={"name": "STALE LINK COPY TEST", "copyFromTenantId": SAMPLE_TENANT},
            )
            assert create.status_code == 200
            new_tenant_id = create.json()["id"]

            copied_cp = client.get(
                f"/ui/checkpoints?tenant_id={new_tenant_id}&active_only=true&page=1&size=50",
                headers=auth_header(TEST_ADMIN_TOKEN),
            ).json()["items"]
            copied_onboarding = next(item for item in copied_cp if item["name"] == "Onboarding")
            copied_links = client.get(
                f"/ui/signals?checkpoint_id={copied_onboarding['id']}&page=1&size=50",
                headers=auth_header(TEST_ADMIN_TOKEN),
            ).json()["items"]
            copied_names = {signal["name"] for signal in copied_links}

            assert "age_check" in copied_names
        finally:
            if old_signal_id and new_signal_id:
                with db_cursor() as (conn, cur):
                    cur.execute(
                        """
                        UPDATE signal_current_version
                           SET signal_id = %s, updated_at = NOW()
                         WHERE tenant_id = %s AND name = 'age_check'
                        """,
                        (old_signal_id, SAMPLE_TENANT),
                    )
                    cur.execute("DELETE FROM signals WHERE id = %s", (new_signal_id,))
                    conn.commit()

    def test_historical_decision_redacts_param_values(self, client):
        from db import db_cursor

        decision_id = "55555555-5555-5555-5555-555555555555"
        signal_log_id = "66666666-6666-6666-6666-666666666666"
        try:
            with db_cursor() as (conn, cur):
                cur.execute(
                    """
                    INSERT INTO decision_log (
                        id, checkpoint_id, tenant_id, applicant_id,
                        final_decision_value, cost_incurred, correlation_id
                    ) VALUES (
                        %s,
                        '22222222-2222-2222-2222-222222222201',
                        %s,
                        'param-redaction-test',
                        'PENDING',
                        0,
                        'param-redaction-correlation'
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (decision_id, SAMPLE_TENANT),
                )
                cur.execute(
                    """
                    INSERT INTO signal_log (
                        id, decision_log_id, signal_id, applicant_id,
                        signal_value, cost_incurred, success
                    ) VALUES (
                        %s, %s, '33333333-3333-3333-3333-333333333301',
                        'param-redaction-test', 'True', 0, TRUE
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (signal_log_id, decision_id),
                )
                cur.execute(
                    """
                    INSERT INTO signal_log_values (signal_log_id, param_name, param_value)
                    VALUES (%s, 'Authorization', 'Bearer leaked-historical-token')
                    """,
                    (signal_log_id,),
                )
                cur.execute(
                    """
                    INSERT INTO signal_log_values (signal_log_id, param_name, param_value)
                    VALUES (%s, 'user_id', '12345')
                    """,
                    (signal_log_id,),
                )
                conn.commit()

            resp = client.get(
                f"/decisions/{decision_id}",
                headers=auth_header(TEST_SAMPLE_TOKEN),
            )
            assert resp.status_code == 200
            params = resp.json()["signals"][0]["param_values"]
            assert params["Authorization"] == "[REDACTED]"
            assert params["user_id"] == "12345"
            assert "leaked-historical-token" not in str(resp.json())
        finally:
            with db_cursor() as (conn, cur):
                cur.execute(
                    "DELETE FROM signal_log_values WHERE signal_log_id = %s",
                    (signal_log_id,),
                )
                cur.execute("DELETE FROM signal_log WHERE id = %s", (signal_log_id,))
                cur.execute("DELETE FROM decision_log WHERE id = %s", (decision_id,))
                conn.commit()

    def test_signal_create_rejects_embedded_authorization_header(self, client):
        resp = client.post(
            "/ui/signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "bad-secret-signal",
                "type": "internal_endpoint",
                "method_of_call": "http://127.0.0.1:8000/mock/onboarding",
                "request_headers_template": "Authorization: Bearer secret-in-template",
            },
        )
        assert resp.status_code == 422
