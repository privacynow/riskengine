-- Test-only visual regression fixture. Apply via scripts/seed_visual_fixture.sh.

INSERT INTO tenants (id, name)
VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'VISUAL FIXTURE BANK')
ON CONFLICT (id) DO UPDATE
   SET name = EXCLUDED.name,
       updated_at = NOW();

INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'Fixture Checkpoint',
  'Stable checkpoint for visual regression.',
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
  'Fixture Checkpoint',
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
    actor_id, promotion_reason, action, source, created_at
)
VALUES (
  'dddddddd-dddd-dddd-dddd-dddddddddddd',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'checkpoint',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  'Fixture Checkpoint',
  'fixture',
  'Seed promote',
  'promote',
  'seed',
  TIMESTAMP '2020-01-01 00:00:00'
)
ON CONFLICT (id) DO UPDATE
   SET tenant_id = EXCLUDED.tenant_id,
       resource_type = EXCLUDED.resource_type,
       resource_id = EXCLUDED.resource_id,
       resource_name = EXCLUDED.resource_name,
       actor_id = EXCLUDED.actor_id,
       promotion_reason = EXCLUDED.promotion_reason,
       action = EXCLUDED.action,
       source = EXCLUDED.source,
       created_at = EXCLUDED.created_at;

UPDATE checkpoints
   SET name = 'Fixture Checkpoint',
       description = 'Stable checkpoint for visual regression.'
 WHERE id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';

UPDATE checkpoint_current_version
   SET checkpoint_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
 WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
   AND name = 'Fixture Checkpoint';

UPDATE promotion_audit
   SET resource_name = 'Fixture Checkpoint'
 WHERE id = 'dddddddd-dddd-dddd-dddd-dddddddddddd';
