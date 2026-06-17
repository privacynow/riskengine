"""Validate demo seed checkpoints execute without missing signal binding errors."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from engine.db import db_cursor
from tests.conftest import OTHER_TENANT, SAMPLE_TENANT, TEST_ADMIN_TOKEN
from tests.seed_reset import SEED_CHECKPOINT_CURRENT

pytestmark = pytest.mark.skipif(
    os.environ.get("DB_HOST", "localhost") == "localhost"
    and not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres (set DB_HOST or RUN_INTEGRATION_TESTS=1)",
)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _fetch_failed_signal_logs(decision_id: str) -> list[tuple[str, str | None]]:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT s.name, sl.error_message
              FROM signal_log sl
              JOIN signals s ON s.id = sl.signal_id
             WHERE sl.decision_log_id = %s
               AND sl.success = FALSE
            """,
            (decision_id,),
        )
        return [(row[0], row[1]) for row in cur.fetchall()]


def _is_missing_binding_error(error_message: str | None) -> bool:
    if not error_message:
        return False
    lowered = error_message.lower()
    return "is not defined" in lowered or "unknown identifier" in lowered


@pytest.fixture
def client() -> TestClient:
    from engine.main import app

    return TestClient(app)


@pytest.mark.parametrize(
    "tenant_id,checkpoint_name",
    [
        (tenant_id, checkpoint_name)
        for tenant_id, names in SEED_CHECKPOINT_CURRENT.items()
        for checkpoint_name in names
    ],
)
def test_seeded_current_checkpoint_executes_without_binding_errors(
    client: TestClient,
    tenant_id: str,
    checkpoint_name: str,
) -> None:
    correlation_id = f"seed-exec-{uuid.uuid4().hex[:12]}"
    response = client.post(
        "/ui/test_decisions",
        headers=auth_header(TEST_ADMIN_TOKEN),
        json={
            "tenant_id": tenant_id,
            "checkpoint_name": checkpoint_name,
            "applicant_id": f"seed-applicant-{correlation_id}",
            "correlation_id": correlation_id,
            "parameters": {},
        },
    )
    assert response.status_code == 200, response.text

    decision_id = response.json()["decision_id"]
    binding_failures = [
        (signal_name, error_message)
        for signal_name, error_message in _fetch_failed_signal_logs(decision_id)
        if _is_missing_binding_error(error_message)
    ]
    assert not binding_failures, (
        f"{checkpoint_name} ({tenant_id}) produced missing-binding signal failures: "
        f"{binding_failures}"
    )
