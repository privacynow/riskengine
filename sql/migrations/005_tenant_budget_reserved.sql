-- In-flight tenant budget leases (atomic pre-vendor reservation)
ALTER TABLE tenant_budgets
    ADD COLUMN IF NOT EXISTS reserved_units INTEGER NOT NULL DEFAULT 0;
