"""Lightweight schema guards for deployments."""

from __future__ import annotations

import time

import psycopg2

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

_SIGNAL_LOG_ERROR_MESSAGE_DDL = """
ALTER TABLE signal_log
    ADD COLUMN IF NOT EXISTS error_message TEXT;
"""


def ensure_schema(max_attempts: int = 30, delay_seconds: float = 1.0) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with db_cursor() as (conn, cur):
                cur.execute(_PROMOTION_AUDIT_DDL)
                cur.execute(_SIGNAL_LOG_ERROR_MESSAGE_DDL)
                conn.commit()
            logger.info("Schema migration checks complete.")
            return
        except psycopg2.OperationalError:
            if attempt >= max_attempts:
                raise
            logger.warning(
                "Database unavailable for schema checks; retrying (%s/%s).",
                attempt,
                max_attempts,
            )
            time.sleep(delay_seconds)
