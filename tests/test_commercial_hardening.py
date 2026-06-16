import time

import jwt
import pytest
from fastapi.testclient import TestClient

from engine.permissions import permissions_for_roles
from engine.services.secret_storage import decrypt_secret, encrypt_secret
from tests.conftest import TEST_ADMIN_TOKEN, TEST_SAMPLE_TOKEN
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
    with pytest.raises(RuntimeError, match="DECISION_ENGINE_SECRET_ENCRYPTION_KEY"):
        encrypt_secret("connector-secret-value")


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
