import os

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_SAMPLE_TOKEN


@pytest.fixture
def client():
    from engine.main import app

    return TestClient(app)


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.skipif(
    os.environ.get("DB_HOST", "localhost") == "localhost"
    and not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres",
)
class TestDecisionRequestValidation:
    def test_malformed_json_returns_422(self, client):
        response = client.post(
            "/decisions",
            headers={**auth_header(TEST_SAMPLE_TOKEN), "Content-Type": "application/json"},
            content=b"{not-json",
        )
        assert response.status_code == 422

    def test_missing_checkpoint_name_returns_422(self, client):
        response = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={"applicant_id": "demo"},
        )
        assert response.status_code == 422

    def test_unknown_field_returns_422(self, client):
        response = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={"checkpoint_name": "Onboarding", "unexpected": True},
        )
        assert response.status_code == 422

    def test_tenant_field_in_body_returns_403(self, client):
        response = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={"checkpoint_name": "Onboarding", "tenant_name": "OTHER BANK"},
        )
        assert response.status_code == 403

    def test_empty_tenant_field_in_body_returns_403(self, client):
        response = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={"checkpoint_name": "Onboarding", "tenant_id": ""},
        )
        assert response.status_code == 403

    def test_null_tenant_field_in_body_returns_403(self, client):
        response = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={"checkpoint_name": "Onboarding", "tenant_name": None},
        )
        assert response.status_code == 403

    def test_empty_tenant_query_param_returns_403(self, client):
        response = client.get(
            "/checkpoints/Onboarding",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            params={"tenant_id": ""},
        )
        assert response.status_code == 403


class TestOpenAPIRuntimeParams:
    def test_runtime_get_paths_do_not_document_tenant_query_params(self, client):
        schema = client.get("/openapi.json").json()
        for path in ("/checkpoints/{checkpoint_name}", "/signals/{signal_name}"):
            get_op = schema["paths"][path]["get"]
            param_names = {p["name"] for p in get_op.get("parameters", [])}
            assert "tenant_id" not in param_names
            assert "tenant_name" not in param_names

    def test_decisions_post_documents_request_body(self, client):
        schema = client.get("/openapi.json").json()
        post_op = schema["paths"]["/decisions"]["post"]
        assert "requestBody" in post_op

    def test_openapi_generation_has_no_duplicate_operation_id_warnings(self, client):
        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            client.get("/openapi.json")
        duplicate_warnings = [
            warning
            for warning in caught
            if "Duplicate Operation ID" in str(warning.message)
        ]
        assert duplicate_warnings == []
