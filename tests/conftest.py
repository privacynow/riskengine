import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_TENANT = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT = "99999999-9999-9999-9999-999999999999"
VISUAL_FIXTURE_TENANT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

TEST_SAMPLE_TOKEN = "test-sample-runtime-token"
TEST_OTHER_TOKEN = "test-other-runtime-token"
TEST_ADMIN_TOKEN = "test-admin-token"

os.environ.pop("DECISION_ENGINE_AUTH_TOKENS_FILE", None)
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ["DECISION_ENGINE_AUTH_TOKENS"] = json.dumps(
    {
        TEST_SAMPLE_TOKEN: {
            "tenant_id": SAMPLE_TENANT,
            "actor_id": "test-sample-client",
            "roles": ["runtime"],
        },
        TEST_OTHER_TOKEN: {
            "tenant_id": OTHER_TENANT,
            "actor_id": "test-other-client",
            "roles": ["runtime"],
        },
        TEST_ADMIN_TOKEN: {
            "tenant_id": None,
            "actor_id": "test-admin",
            "roles": ["admin"],
        },
    }
)

from engine.config import validate_config
from engine.auth import initialize_auth

validate_config()
initialize_auth()


def _integration_tests_enabled() -> bool:
    return bool(os.environ.get("RUN_INTEGRATION_TESTS")) or os.environ.get(
        "DB_HOST", "localhost"
    ) != "localhost"


@pytest.fixture(autouse=True)
def _reset_integration_seed_state():
    if not _integration_tests_enabled():
        yield
        return
    from tests.seed_reset import reset_integration_seed_state

    reset_integration_seed_state()
    yield
    reset_integration_seed_state()
