import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from engine.permissions import permissions_for_roles
from engine.services.secret_storage import (
    SecretEncryptionNotConfiguredError,
    decrypt_secret,
    encrypt_secret,
)
from tests.conftest import (
    SAMPLE_TENANT,
    TEST_ADMIN_READONLY_TOKEN,
    TEST_ADMIN_TOKEN,
    TEST_AUDIT_VIEWER_TOKEN,
    TEST_CONFIG_OPERATOR_TOKEN,
    TEST_SAMPLE_TOKEN,
    TEST_TEST_RUNNER_TOKEN,
    TEST_TENANT_ADMIN_TOKEN,
)
from tests.test_admin import auth_header


def test_encrypt_decrypt_roundtrip(monkeypatch):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("DECISION_ENGINE_SECRET_ENCRYPTION_KEY", key)
    stored = encrypt_secret("connector-secret-value")
    assert stored.startswith("enc:v1:")
    assert decrypt_secret(stored) == "connector-secret-value"


def test_encrypt_secret_requires_encryption_key(monkeypatch):
    monkeypatch.delenv("DECISION_ENGINE_SECRET_ENCRYPTION_KEY", raising=False)
    with pytest.raises(SecretEncryptionNotConfiguredError):
        encrypt_secret("connector-secret-value")


def test_signal_create_without_encryption_key_returns_503(monkeypatch):
    from engine.main import app

    monkeypatch.delenv("DECISION_ENGINE_SECRET_ENCRYPTION_KEY", raising=False)
    client = TestClient(app)
    response = client.post(
        "/ui/signals",
        headers=auth_header(TEST_ADMIN_TOKEN),
        json={
            "tenant_id": SAMPLE_TENANT,
            "name": "encryption-key-missing-signal",
            "description": "Should fail closed",
            "type": "expression",
            "expression_body": "True",
            "cost": 1,
            "cache_expiration_seconds": 0,
            "timeout_seconds": 5,
            "can_run_in_parallel": False,
            "order_of_evaluation": 1,
            "bearer_token": "super-secret-token",
        },
    )
    assert response.status_code == 503
    assert "DECISION_ENGINE_SECRET_ENCRYPTION_KEY" in response.json()["detail"]


def test_admin_signal_api_never_returns_bearer_token():
    from engine.main import app

    client = TestClient(app)
    signal_id = "33333333-3333-3333-3333-333333333305"
    response = client.get(
        f"/ui/signals/{signal_id}",
        headers=auth_header(TEST_ADMIN_TOKEN),
    )
    assert response.status_code == 200
    body = response.json()
    assert "bearer_token" not in body
    assert body.get("has_bearer_token") in (True, False)


def test_jwt_only_startup_admin_request(monkeypatch):
    import importlib

    import engine.main as main_module

    secret = "jwt-only-test-secret"
    monkeypatch.delenv("DECISION_ENGINE_AUTH_TOKENS", raising=False)
    monkeypatch.delenv("DECISION_ENGINE_AUTH_TOKENS_FILE", raising=False)
    monkeypatch.setenv("DECISION_ENGINE_JWT_HS256_SECRET", secret)
    importlib.reload(main_module)
    token = jwt.encode(
        {
            "sub": "jwt-admin",
            "roles": ["admin"],
            "exp": int(time.time()) + 3600,
        },
        secret,
        algorithm="HS256",
    )
    client = TestClient(main_module.app)
    response = client.get(
        "/ui/tenants?page=1&size=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_jwt_auth_admin_request(monkeypatch):
    import importlib

    import engine.main as main_module

    secret = "jwt-test-secret"
    monkeypatch.setenv("DECISION_ENGINE_JWT_HS256_SECRET", secret)
    importlib.reload(main_module)
    token = jwt.encode(
        {
            "sub": "jwt-admin",
            "roles": ["admin"],
            "exp": int(time.time()) + 3600,
        },
        secret,
        algorithm="HS256",
    )
    client = TestClient(main_module.app)
    response = client.get(
        "/ui/tenants?page=1&size=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_runtime_token_denied_admin_read():
    from engine.main import app

    client = TestClient(app)
    response = client.get(
        "/ui/tenants?page=1&size=1",
        headers=auth_header(TEST_SAMPLE_TOKEN),
    )
    assert response.status_code == 403


def test_permissions_for_runtime_role():
    perms = permissions_for_roles(frozenset({"runtime"}))
    assert "runtime:execute" in perms
    assert "admin:write" not in perms


def test_audit_viewer_can_read_promotion_audit():
    from engine.main import app

    client = TestClient(app)
    response = client.get(
        "/ui/promotion_audit?page=1&size=1",
        headers=auth_header(TEST_AUDIT_VIEWER_TOKEN),
    )
    assert response.status_code == 200


def test_audit_viewer_denied_admin_write():
    from engine.main import app

    client = TestClient(app)
    response = client.post(
        "/ui/checkpoints",
        headers=auth_header(TEST_AUDIT_VIEWER_TOKEN),
        json={
            "tenant_id": SAMPLE_TENANT,
            "name": "audit-viewer-denied",
            "description": "Should fail",
            "type": "fixture",
            "dsl_expression": "True",
            "method_of_call": "http://127.0.0.1:8000/mock/fixture",
            "max_cost": 10,
            "override_cost_flag": False,
            "timeout_seconds": 30,
        },
    )
    assert response.status_code == 403


def test_config_operator_can_deactivate_checkpoint():
    from engine.main import app

    admin = TestClient(app)
    checkpoint_name = f"permission-boundary-{uuid.uuid4().hex[:8]}"
    created = admin.post(
        "/ui/checkpoints",
        headers=auth_header(TEST_ADMIN_TOKEN),
        json={
            "tenant_id": SAMPLE_TENANT,
            "name": checkpoint_name,
            "description": "Scratch checkpoint for config:deactivate permission test",
            "type": "fixture",
            "dsl_expression": "True",
            "method_of_call": "http://127.0.0.1:8000/mock/fixture",
            "max_cost": 10,
            "override_cost_flag": False,
            "timeout_seconds": 30,
        },
    )
    assert created.status_code == 200
    checkpoint_id = created.json()["id"]

    promoted = admin.post(
        f"/ui/checkpoints/{checkpoint_id}/make_current",
        headers=auth_header(TEST_ADMIN_TOKEN),
        json={"promotion_reason": "Permission boundary scratch setup"},
    )
    assert promoted.status_code == 200

    deactivated = False
    try:
        response = admin.post(
            f"/ui/checkpoints/{checkpoint_id}/deactivate",
            headers=auth_header(TEST_CONFIG_OPERATOR_TOKEN),
            json={"promotion_reason": "Permission boundary deactivate test"},
        )
        assert response.status_code == 200
        deactivated = True
    finally:
        if deactivated:
            cleanup = admin.post(
                f"/ui/checkpoints/{checkpoint_id}/reactivate",
                headers=auth_header(TEST_ADMIN_TOKEN),
                json={"promotion_reason": "Permission boundary scratch cleanup"},
            )
            assert cleanup.status_code == 200


def test_config_operator_denied_tenant_manage():
    from engine.main import app

    client = TestClient(app)
    response = client.post(
        "/ui/tenants",
        headers=auth_header(TEST_CONFIG_OPERATOR_TOKEN),
        json={"name": "config-operator-denied"},
    )
    assert response.status_code == 403


def test_test_runner_denied_checkpoint_write():
    from engine.main import app

    client = TestClient(app)
    response = client.post(
        "/ui/checkpoints",
        headers=auth_header(TEST_TEST_RUNNER_TOKEN),
        json={
            "tenant_id": SAMPLE_TENANT,
            "name": "test-runner-denied",
            "description": "Should fail",
            "type": "fixture",
            "dsl_expression": "True",
            "method_of_call": "http://127.0.0.1:8000/mock/fixture",
            "max_cost": 10,
            "override_cost_flag": False,
            "timeout_seconds": 30,
        },
    )
    assert response.status_code == 403


def test_tenant_admin_can_create_tenant():
    from engine.main import app

    client = TestClient(app)
    response = client.post(
        "/ui/tenants",
        headers=auth_header(TEST_TENANT_ADMIN_TOKEN),
        json={"name": "tenant-admin-created"},
    )
    assert response.status_code == 200


def test_tenant_admin_denied_audit_read():
    from engine.main import app

    client = TestClient(app)
    response = client.get(
        "/ui/promotion_audit?page=1&size=1",
        headers=auth_header(TEST_TENANT_ADMIN_TOKEN),
    )
    assert response.status_code == 403


def test_admin_readonly_can_list_tenants():
    from engine.main import app

    client = TestClient(app)
    response = client.get(
        "/ui/tenants?page=1&size=1",
        headers=auth_header(TEST_ADMIN_READONLY_TOKEN),
    )
    assert response.status_code == 200


def test_admin_readonly_denied_checkpoint_write():
    from engine.main import app

    client = TestClient(app)
    response = client.post(
        "/ui/checkpoints",
        headers=auth_header(TEST_ADMIN_READONLY_TOKEN),
        json={
            "tenant_id": SAMPLE_TENANT,
            "name": "admin-readonly-denied",
            "description": "Should fail",
            "type": "fixture",
            "dsl_expression": "True",
            "method_of_call": "http://127.0.0.1:8000/mock/fixture",
            "max_cost": 10,
            "override_cost_flag": False,
            "timeout_seconds": 30,
        },
    )
    assert response.status_code == 403


@pytest.mark.skipif(
    not __import__("os").environ.get("RUN_INTEGRATION_TESTS"),
    reason="Requires integration DB for test lab execution",
)
def test_test_runner_can_execute_test_decision():
    from engine.main import app

    client = TestClient(app)
    response = client.post(
        "/ui/test_decisions",
        headers=auth_header(TEST_TEST_RUNNER_TOKEN),
        json={
            "tenant_id": SAMPLE_TENANT,
            "checkpoint_name": "Onboarding",
            "applicant_id": "permission-boundary-applicant",
            "correlation_id": "permission-boundary-correlation",
            "parameters": {},
        },
    )
    assert response.status_code == 200
    assert response.json()["final_decision_value"] in ("True", "False")
