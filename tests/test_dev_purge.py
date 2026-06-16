import importlib

import pytest
from fastapi.testclient import TestClient

from engine.services.dev_purge import DEV_PURGE_BODY_PHRASE
from tests.conftest import SAMPLE_TENANT, TEST_ADMIN_TOKEN
from tests.test_admin import auth_header


def reload_test_client() -> TestClient:
    import engine.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


@pytest.fixture
def client():
    return reload_test_client()


@pytest.fixture
def enable_dev_purge(monkeypatch):
    monkeypatch.setenv("DECISION_ENGINE_DEV_PURGE", "1")
    monkeypatch.setenv("DECISION_ENGINE_DEV_PURGE_CONFIRM", "test-dev-purge-confirm")


@pytest.fixture
def dev_purge_client(enable_dev_purge):
    return reload_test_client()


def test_dev_purge_status_hidden_when_disabled(client):
    response = client.get(
        "/ui/dev/purge/status",
        headers=auth_header(TEST_ADMIN_TOKEN),
    )
    assert response.status_code == 404


def test_dev_purge_status_hidden_when_disabled_without_auth(client):
    response = client.get("/ui/dev/purge/status")
    assert response.status_code == 404


def test_dev_purge_status_visible_when_enabled(dev_purge_client):
    response = dev_purge_client.get(
        "/ui/dev/purge/status",
        headers=auth_header(TEST_ADMIN_TOKEN),
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_dev_purge_refuses_when_confirm_not_configured(monkeypatch):
    monkeypatch.setenv("DECISION_ENGINE_DEV_PURGE", "1")
    monkeypatch.delenv("DECISION_ENGINE_DEV_PURGE_CONFIRM", raising=False)
    client = reload_test_client()

    status = client.get(
        "/ui/dev/purge/status",
        headers=auth_header(TEST_ADMIN_TOKEN),
    )
    assert status.status_code == 500

    purge = client.post(
        "/ui/dev/purge/tenant",
        headers={
            **auth_header(TEST_ADMIN_TOKEN),
            "X-Dev-Purge-Confirm": "purge-dev-tenant-data",
        },
        json={
            "tenantId": SAMPLE_TENANT,
            "purgeReason": "Integration test purge",
            "confirmPhrase": DEV_PURGE_BODY_PHRASE,
        },
    )
    assert purge.status_code == 500


def test_dev_purge_requires_confirm_header(dev_purge_client):
    response = dev_purge_client.post(
        "/ui/dev/purge/tenant",
        headers=auth_header(TEST_ADMIN_TOKEN),
        json={
            "tenantId": SAMPLE_TENANT,
            "purgeReason": "Integration test purge",
            "confirmPhrase": DEV_PURGE_BODY_PHRASE,
        },
    )
    assert response.status_code == 403


def test_dev_purge_requires_body_phrase(dev_purge_client):
    response = dev_purge_client.post(
        "/ui/dev/purge/tenant",
        headers={
            **auth_header(TEST_ADMIN_TOKEN),
            "X-Dev-Purge-Confirm": "test-dev-purge-confirm",
        },
        json={
            "tenantId": SAMPLE_TENANT,
            "purgeReason": "Integration test purge",
            "confirmPhrase": "wrong phrase",
        },
    )
    assert response.status_code == 422


def test_dev_purge_clears_audit_rows(dev_purge_client):
    dev_purge_client.post(
        "/ui/test_decisions",
        headers=auth_header(TEST_ADMIN_TOKEN),
        json={
            "tenant_id": SAMPLE_TENANT,
            "checkpoint_name": "Onboarding",
            "correlation_id": "dev-purge-test",
        },
    )
    audit_before = dev_purge_client.get(
        f"/ui/search_decisions?tenant_id={SAMPLE_TENANT}&q=dev-purge-test&page=1&size=5",
        headers=auth_header(TEST_ADMIN_TOKEN),
    ).json()["items"]
    assert audit_before

    purge = dev_purge_client.post(
        "/ui/dev/purge/tenant",
        headers={
            **auth_header(TEST_ADMIN_TOKEN),
            "X-Dev-Purge-Confirm": "test-dev-purge-confirm",
        },
        json={
            "tenantId": SAMPLE_TENANT,
            "purgeReason": "Integration test purge of audit rows",
            "confirmPhrase": DEV_PURGE_BODY_PHRASE,
        },
    )
    assert purge.status_code == 200
    deleted = purge.json()["deleted"]
    assert deleted["decision_log"] >= 1

    audit_after = dev_purge_client.get(
        f"/ui/search_decisions?tenant_id={SAMPLE_TENANT}&q=dev-purge-test&page=1&size=5",
        headers=auth_header(TEST_ADMIN_TOKEN),
    ).json()["items"]
    assert not audit_after


def test_list_signal_variable_values(client):
    signal_id = "33333333-3333-3333-3333-333333333301"
    response = client.get(
        f"/ui/signals/{signal_id}/variable_values?page=1&size=10",
        headers=auth_header(TEST_ADMIN_TOKEN),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    assert items[0]["name"] == "age_check"
