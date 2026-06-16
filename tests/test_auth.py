import os

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_ADMIN_TOKEN, TEST_OTHER_TOKEN, TEST_SAMPLE_TOKEN

SAMPLE_TENANT = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT = "99999999-9999-9999-9999-999999999999"


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
class TestAuthIntegration:
    def test_no_auth_returns_401(self, client):
        assert client.post("/decisions", json={"checkpoint_name": "Onboarding"}).status_code == 401
        assert client.get("/checkpoints/Onboarding").status_code == 401

    def test_runtime_token_derives_tenant(self, client):
        resp = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={
                "checkpoint_name": "Onboarding",
                "applicant_id": "pytest",
                "correlation_id": "pytest",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["final_decision_value"] == "True"

    def test_supplied_tenant_in_body_rejected(self, client):
        resp = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={
                "checkpoint_name": "Onboarding",
                "tenant_name": "OTHER BANK",
            },
        )
        assert resp.status_code == 403

    def test_cross_tenant_query_rejected(self, client):
        resp = client.get(
            "/checkpoints/Onboarding",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            params={"tenant_name": "OTHER BANK"},
        )
        assert resp.status_code == 403

    def test_same_checkpoint_name_resolves_by_auth(self, client):
        sample = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={"checkpoint_name": "Onboarding", "correlation_id": "x"},
        ).json()
        other = client.post(
            "/decisions",
            headers=auth_header(TEST_OTHER_TOKEN),
            json={"checkpoint_name": "Onboarding", "correlation_id": "y"},
        ).json()
        assert sample["final_decision_value"] == "True"
        assert other["final_decision_value"] == "False"

    def test_inactive_signal_not_executed(self, client):
        resp = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={"checkpoint_name": "Onboarding", "correlation_id": "inactive-test"},
        )
        assert "inactive_demo" not in resp.json()["signal_results"]

    def test_admin_can_access_ui(self, client):
        assert client.get("/ui/tenants", headers=auth_header(TEST_ADMIN_TOKEN)).status_code == 200

    def test_demo_runtime_tokens_endpoint_removed(self, client):
        assert client.get("/ui/demo_runtime_tokens", headers=auth_header(TEST_ADMIN_TOKEN)).status_code == 404

    def test_admin_test_decision_runs_server_side(self, client):
        resp = client.post(
            "/ui/test_decisions",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "checkpoint_name": "Onboarding",
                "correlation_id": "admin-ui-test",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["final_decision_value"] == "True"

    def test_runtime_checkpoint_response_omits_signal_bearer_token(self, client):
        resp = client.get(
            "/checkpoints/Onboarding",
            headers=auth_header(TEST_SAMPLE_TOKEN),
        )
        assert resp.status_code == 200
        body = resp.json()
        for signal in body.get("signals", []):
            assert "bearer_token" not in signal
            assert "has_bearer_token" not in signal
            assert "request_headers_template" not in signal
            assert "request_body_template" not in signal

    def test_runtime_signal_response_omits_bearer_token(self, client):
        resp = client.get(
            "/signals/kyc_score",
            headers=auth_header(TEST_SAMPLE_TOKEN),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "bearer_token" not in body
        assert "has_bearer_token" not in body

    def test_admin_signal_list_masks_bearer_token(self, client):
        resp = client.get("/ui/signals?page=1&size=5", headers=auth_header(TEST_ADMIN_TOKEN))
        assert resp.status_code == 200
        for signal in resp.json()["items"]:
            assert "bearer_token" not in signal
            assert "has_bearer_token" in signal


class TestAuthUnit:
    def test_auth_configured_in_tests(self):
        from auth import get_token_map

        token_map = get_token_map()
        assert TEST_SAMPLE_TOKEN in token_map
        assert token_map[TEST_SAMPLE_TOKEN]["tenant_id"] == SAMPLE_TENANT
        assert token_map[TEST_OTHER_TOKEN]["tenant_id"] == OTHER_TENANT
        assert "admin" in token_map[TEST_ADMIN_TOKEN]["roles"]
