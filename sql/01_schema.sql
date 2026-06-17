-- ==========================================================================
-- DDL Script (schema.sql)
-- ==========================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- tenants
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- checkpoints
CREATE TABLE IF NOT EXISTS checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(100) NOT NULL,
    dsl_expression TEXT NOT NULL,
    method_of_call TEXT,
    max_cost INTEGER,
    override_cost_flag BOOLEAN NOT NULL DEFAULT FALSE,
    budget_exceeded_policy VARCHAR(20) NOT NULL DEFAULT 'refer',
    vendor_failure_policy VARCHAR(20) NOT NULL DEFAULT 'refer',
    terminal_decline_signal_names TEXT[] NOT NULL DEFAULT '{}',
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- signals
CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    method_of_call TEXT,
    expression_body TEXT,
    cost INTEGER NOT NULL DEFAULT 0,
    cache_expiration_seconds INTEGER NOT NULL DEFAULT 0,
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    can_run_in_parallel BOOLEAN NOT NULL DEFAULT FALSE,
    order_of_evaluation INTEGER NOT NULL DEFAULT 1,
    http_method VARCHAR(10),
    request_url_params_template TEXT,
    request_body_template TEXT,
    request_headers_template TEXT,
    -- Outbound connector token; encrypted at rest (enc:v1:) when DECISION_ENGINE_SECRET_ENCRYPTION_KEY is set.
    -- Admin API never returns the value (has_bearer_token only).
    bearer_token TEXT,
    allow_caching BOOLEAN NOT NULL DEFAULT FALSE,
    global_reuse BOOLEAN NOT NULL DEFAULT FALSE,
    function_params_template TEXT,
    default_priority INTEGER NOT NULL DEFAULT 500,
    billable_event VARCHAR(20) NOT NULL DEFAULT 'success',
    cache_scope VARCHAR(40) NOT NULL DEFAULT 'tenant_applicant_signal',
    vendor_name VARCHAR(255),
    vendor_product VARCHAR(255),
    is_expensive_vendor BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- checkpoint_signals
CREATE TABLE IF NOT EXISTS checkpoint_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    checkpoint_id UUID NOT NULL REFERENCES checkpoints (id),
    signal_id UUID NOT NULL REFERENCES signals (id),
    priority_override INTEGER,
    criticality VARCHAR(20) NOT NULL DEFAULT 'preferred',
    execution_role VARCHAR(40) NOT NULL DEFAULT 'referenced_policy',
    stage_override INTEGER,
    vendor_audit_after_decline BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

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

-- decision_log
CREATE TABLE IF NOT EXISTS decision_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    checkpoint_id UUID NOT NULL REFERENCES checkpoints (id),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    applicant_id VARCHAR(255),
    final_decision_value VARCHAR(255),
    decision_outcome VARCHAR(32) NOT NULL,
    decision_reason VARCHAR(64),
    degraded BOOLEAN NOT NULL DEFAULT FALSE,
    cost_incurred INTEGER NOT NULL DEFAULT 0,
    estimated_cost_units INTEGER NOT NULL DEFAULT 0,
    reserved_cost_units INTEGER NOT NULL DEFAULT 0,
    actual_cost_units INTEGER NOT NULL DEFAULT 0,
    budget_units INTEGER,
    correlation_id VARCHAR(255),
    decision_timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- signal_log
CREATE TABLE IF NOT EXISTS signal_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_log_id UUID NOT NULL REFERENCES decision_log (id),
    signal_id UUID NOT NULL REFERENCES signals (id),
    applicant_id VARCHAR(255),
    signal_value VARCHAR(255),
    started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    cost_incurred INTEGER NOT NULL DEFAULT 0,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    execution_status VARCHAR(32),
    criticality VARCHAR(20),
    estimated_cost_units INTEGER NOT NULL DEFAULT 0,
    reserved_cost_units INTEGER NOT NULL DEFAULT 0,
    actual_cost_units INTEGER NOT NULL DEFAULT 0,
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    skip_reason_code VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- signal_log_values
CREATE TABLE IF NOT EXISTS signal_log_values (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_log_id UUID NOT NULL REFERENCES signal_log(id),
    param_name VARCHAR(255),
    param_value TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- signal_cached_values (DB-based caching; matches runtime queries in main.py)
CREATE TABLE IF NOT EXISTS signal_cached_values (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    checkpoint_id UUID,
    signal_id UUID NOT NULL REFERENCES signals (id),
    applicant_id VARCHAR(255),
    signal_value TEXT,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS signal_cached_values_checkpoint_scope_idx
  ON signal_cached_values (
    tenant_id,
    checkpoint_id,
    signal_id,
    COALESCE(applicant_id, ''::varchar)
  )
  WHERE checkpoint_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS signal_cached_values_tenant_signal_applicant_idx
  ON signal_cached_values (
    tenant_id,
    signal_id,
    COALESCE(applicant_id, ''::varchar)
  )
  WHERE checkpoint_id IS NULL;

CREATE INDEX IF NOT EXISTS signal_cached_values_lookup_idx
  ON signal_cached_values (tenant_id, signal_id, applicant_id);

-- per-signal stored variable values
CREATE TABLE IF NOT EXISTS signal_variable_values (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID NOT NULL REFERENCES signals (id),
    name VARCHAR(255),
    value TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS signal_variable_values_signal_name_idx
  ON signal_variable_values (signal_id, name);

-- current version pointers
CREATE TABLE IF NOT EXISTS checkpoint_current_version (
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    name VARCHAR(255) NOT NULL,
    checkpoint_id UUID NOT NULL REFERENCES checkpoints (id),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, name)
);

CREATE TABLE IF NOT EXISTS signal_current_version (
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    name VARCHAR(255) NOT NULL,
    signal_id UUID NOT NULL REFERENCES signals (id),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, name)
);

-- promotion audit (governed version promotion)
CREATE TABLE IF NOT EXISTS promotion_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    resource_type VARCHAR(32) NOT NULL,
    resource_id UUID NOT NULL,
    resource_name VARCHAR(255) NOT NULL,
    actor_id VARCHAR(255) NOT NULL,
    promotion_reason TEXT NOT NULL,
    action VARCHAR(32) NOT NULL DEFAULT 'promote',
    source VARCHAR(64) NOT NULL DEFAULT 'make_current',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS promotion_audit_tenant_created_idx
    ON promotion_audit (tenant_id, created_at DESC);
