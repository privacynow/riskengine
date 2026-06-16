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
    max_cost INTEGER NOT NULL DEFAULT 0,
    override_cost_flag BOOLEAN NOT NULL DEFAULT FALSE,
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
    -- Demo-only: outbound connector token stored plaintext; API reads return has_bearer_token only.
    bearer_token TEXT,
    allow_caching BOOLEAN NOT NULL DEFAULT FALSE,
    global_reuse BOOLEAN NOT NULL DEFAULT FALSE,
    function_params_template TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- checkpoint_signals
CREATE TABLE IF NOT EXISTS checkpoint_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    checkpoint_id UUID NOT NULL REFERENCES checkpoints (id),
    signal_id UUID NOT NULL REFERENCES signals (id),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- decision_log
CREATE TABLE IF NOT EXISTS decision_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    checkpoint_id UUID NOT NULL REFERENCES checkpoints (id),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    applicant_id VARCHAR(255),
    final_decision_value VARCHAR(255) NOT NULL,
    cost_incurred INTEGER NOT NULL DEFAULT 0,
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
    checkpoint_id UUID NOT NULL REFERENCES checkpoints (id),
    signal_id UUID NOT NULL REFERENCES signals (id),
    applicant_id VARCHAR(255),
    signal_value TEXT,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS signal_cached_values_unique_idx
  ON signal_cached_values (
    tenant_id,
    checkpoint_id,
    signal_id,
    COALESCE(applicant_id, ''::varchar)
  );

CREATE INDEX IF NOT EXISTS signal_cached_values_lookup_idx
  ON signal_cached_values (tenant_id, checkpoint_id, signal_id, applicant_id);

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
