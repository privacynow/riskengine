"""Lightweight schema guards for prototype deployments."""

from __future__ import annotations

from .config import logger
from .db import db_cursor

_PROMOTION_AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS promotion_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    resource_type VARCHAR(32) NOT NULL,
    resource_id UUID NOT NULL,
    resource_name VARCHAR(255) NOT NULL,
    actor_id VARCHAR(255) NOT NULL,
    promotion_reason TEXT NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'make_current',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS promotion_audit_tenant_created_idx
    ON promotion_audit (tenant_id, created_at DESC);
"""

_VISUAL_FIXTURE_SQL = """
INSERT INTO tenants (id, name)
SELECT 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'VISUAL FIXTURE BANK'
WHERE NOT EXISTS (
  SELECT 1 FROM tenants WHERE id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
);

INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'Fixture Flow',
  'Stable flow for visual regression.',
  'fixture',
  'fixture_signal',
  'http://127.0.0.1:8000/mock/fixture',
  10,
  FALSE,
  30
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoints WHERE id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
);

INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call,
    expression_body, cost, cache_expiration_seconds, timeout_seconds,
    can_run_in_parallel, order_of_evaluation
)
SELECT
  'cccccccc-cccc-cccc-cccc-cccccccccccc',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'fixture_signal',
  'Stable signal for visual regression.',
  'expression',
  NULL,
  'True',
  1,
  0,
  5,
  FALSE,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM signals WHERE id = 'cccccccc-cccc-cccc-cccc-cccccccccccc'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT
  'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  'cccccccc-cccc-cccc-cccc-cccccccccccc'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals WHERE id = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'
);

INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
SELECT
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'Fixture Flow',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
ON CONFLICT (tenant_id, name) DO UPDATE
   SET checkpoint_id = EXCLUDED.checkpoint_id,
       updated_at = NOW();

INSERT INTO signal_current_version (tenant_id, name, signal_id)
SELECT
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'fixture_signal',
  'cccccccc-cccc-cccc-cccc-cccccccccccc'
ON CONFLICT (tenant_id, name) DO UPDATE
   SET signal_id = EXCLUDED.signal_id,
       updated_at = NOW();

INSERT INTO promotion_audit (
    id, tenant_id, resource_type, resource_id, resource_name,
    actor_id, promotion_reason, source, created_at
)
SELECT
  'dddddddd-dddd-dddd-dddd-dddddddddddd',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'checkpoint',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  'Fixture Flow',
  'visual-fixture',
  'Visual fixture seeded promotion',
  'seed',
  TIMESTAMP '2020-01-01 00:00:00'
WHERE NOT EXISTS (
  SELECT 1 FROM promotion_audit WHERE id = 'dddddddd-dddd-dddd-dddd-dddddddddddd'
);
"""


def ensure_schema() -> None:
    with db_cursor() as (conn, cur):
        cur.execute(_PROMOTION_AUDIT_DDL)
        cur.execute(_VISUAL_FIXTURE_SQL)
        conn.commit()
    logger.info("Schema migration checks complete.")
