-- Scratch checkpoint for lifecycle Playwright e2e. Same tenant as visual fixture;
-- must not share promotion_audit rows used by visual-review.spec.ts snapshots.

INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  'ffffffff-ffff-ffff-ffff-ffffffffffff',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'Lifecycle E2E Checkpoint',
  'Isolated checkpoint for lifecycle e2e deactivate/reactivate.',
  'fixture',
  'lifecycle_e2e_signal',
  'http://127.0.0.1:8000/mock/fixture',
  10,
  FALSE,
  30
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoints WHERE id = 'ffffffff-ffff-ffff-ffff-ffffffffffff'
);

INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call,
    expression_body, cost, cache_expiration_seconds, timeout_seconds,
    can_run_in_parallel, order_of_evaluation
)
SELECT
  'f1f1f1f1-f1f1-f1f1-f1f1-f1f1f1f1f1f1',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'lifecycle_e2e_signal',
  'Signal for lifecycle e2e scratch checkpoint.',
  'expression',
  NULL,
  'True',
  1,
  0,
  5,
  FALSE,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM signals WHERE id = 'f1f1f1f1-f1f1-f1f1-f1f1-f1f1f1f1f1f1'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT
  'f2f2f2f2-f2f2-f2f2-f2f2-f2f2f2f2f2f2',
  'ffffffff-ffff-ffff-ffff-ffffffffffff',
  'f1f1f1f1-f1f1-f1f1-f1f1-f1f1f1f1f1f1'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals WHERE id = 'f2f2f2f2-f2f2-f2f2-f2f2f2f2f2f2f2f2'
);

INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
SELECT
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'Lifecycle E2E Checkpoint',
  'ffffffff-ffff-ffff-ffff-ffffffffffff'
ON CONFLICT (tenant_id, name) DO UPDATE
   SET checkpoint_id = EXCLUDED.checkpoint_id,
       updated_at = NOW();

UPDATE checkpoints
   SET name = 'Lifecycle E2E Checkpoint',
       description = 'Isolated checkpoint for lifecycle e2e deactivate/reactivate.',
       dsl_expression = 'lifecycle_e2e_signal'
 WHERE id = 'ffffffff-ffff-ffff-ffff-ffffffffffff';
