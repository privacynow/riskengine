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
