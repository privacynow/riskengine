-- Promotion audit trail for governed lifecycle actions.
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
