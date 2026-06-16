import os

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
