-- Execution planner: dependency-aware scheduling, outcomes, tenant budgets.

-- signals: planner defaults
ALTER TABLE signals ADD COLUMN IF NOT EXISTS default_priority INTEGER NOT NULL DEFAULT 500;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS billable_event VARCHAR(20) NOT NULL DEFAULT 'success';
ALTER TABLE signals ADD COLUMN IF NOT EXISTS cache_scope VARCHAR(40) NOT NULL DEFAULT 'tenant_applicant_signal';
ALTER TABLE signals ADD COLUMN IF NOT EXISTS vendor_name VARCHAR(255);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS vendor_product VARCHAR(255);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS is_expensive_vendor BOOLEAN NOT NULL DEFAULT FALSE;

-- checkpoints: nullable budget + policies
ALTER TABLE checkpoints ALTER COLUMN max_cost DROP NOT NULL;
ALTER TABLE checkpoints ADD COLUMN IF NOT EXISTS budget_exceeded_policy VARCHAR(20) NOT NULL DEFAULT 'refer';
ALTER TABLE checkpoints ADD COLUMN IF NOT EXISTS vendor_failure_policy VARCHAR(20) NOT NULL DEFAULT 'refer';
ALTER TABLE checkpoints ADD COLUMN IF NOT EXISTS terminal_decline_signal_names TEXT[] NOT NULL DEFAULT '{}';

-- checkpoint_signals: per-association execution policy
ALTER TABLE checkpoint_signals ADD COLUMN IF NOT EXISTS priority_override INTEGER;
ALTER TABLE checkpoint_signals ADD COLUMN IF NOT EXISTS criticality VARCHAR(20) NOT NULL DEFAULT 'preferred';
ALTER TABLE checkpoint_signals ADD COLUMN IF NOT EXISTS execution_role VARCHAR(40) NOT NULL DEFAULT 'referenced_policy';
ALTER TABLE checkpoint_signals ADD COLUMN IF NOT EXISTS stage_override INTEGER;
ALTER TABLE checkpoint_signals ADD COLUMN IF NOT EXISTS vendor_audit_after_decline BOOLEAN NOT NULL DEFAULT FALSE;

-- tenant period budgets
CREATE TABLE IF NOT EXISTS tenant_budgets (
    tenant_id UUID PRIMARY KEY REFERENCES tenants (id),
    window_days INTEGER NOT NULL DEFAULT 30,
    window_mode VARCHAR(20) NOT NULL DEFAULT 'anchored',
    limit_units INTEGER NOT NULL DEFAULT 100000,
    used_units INTEGER NOT NULL DEFAULT 0,
    window_anchor TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- decision_log: structured outcomes and cost breakdown
ALTER TABLE decision_log ADD COLUMN IF NOT EXISTS decision_outcome VARCHAR(32);
ALTER TABLE decision_log ADD COLUMN IF NOT EXISTS decision_reason VARCHAR(64);
ALTER TABLE decision_log ADD COLUMN IF NOT EXISTS degraded BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE decision_log ADD COLUMN IF NOT EXISTS estimated_cost_units INTEGER NOT NULL DEFAULT 0;
ALTER TABLE decision_log ADD COLUMN IF NOT EXISTS reserved_cost_units INTEGER NOT NULL DEFAULT 0;
ALTER TABLE decision_log ADD COLUMN IF NOT EXISTS actual_cost_units INTEGER NOT NULL DEFAULT 0;
ALTER TABLE decision_log ADD COLUMN IF NOT EXISTS budget_units INTEGER;

UPDATE decision_log
   SET decision_outcome = CASE
         WHEN final_decision_value IN ('True', 'true', 'APPROVE') THEN 'APPROVE'
         WHEN final_decision_value IN ('False', 'false', 'DECLINE') THEN 'DECLINE'
         ELSE COALESCE(decision_outcome, 'DECLINE')
       END,
       actual_cost_units = cost_incurred
 WHERE decision_outcome IS NULL;

-- signal_log: execution trace fields
ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS execution_status VARCHAR(32);
ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS criticality VARCHAR(20);
ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS estimated_cost_units INTEGER NOT NULL DEFAULT 0;
ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS reserved_cost_units INTEGER NOT NULL DEFAULT 0;
ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS actual_cost_units INTEGER NOT NULL DEFAULT 0;
ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS cache_hit BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS skip_reason_code VARCHAR(64);

UPDATE signal_log
   SET actual_cost_units = cost_incurred,
       execution_status = CASE WHEN success THEN 'ran' ELSE COALESCE(execution_status, 'failed') END
 WHERE execution_status IS NULL;

-- cache: tenant+signal+applicant scope (nullable checkpoint for scoped modes)
ALTER TABLE signal_cached_values ALTER COLUMN checkpoint_id DROP NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS signal_cached_values_tenant_signal_applicant_idx
  ON signal_cached_values (
    tenant_id,
    signal_id,
    COALESCE(applicant_id, ''::varchar)
  )
  WHERE checkpoint_id IS NULL;
