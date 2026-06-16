"""Ordered SQL migrations applied at startup."""

from __future__ import annotations

import time
from pathlib import Path

import psycopg2

from .config import logger
from .db import db_cursor

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "sql" / "migrations"

_SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
"""


def _migration_files() -> list[Path]:
    if not MIGRATIONS_DIR.is_dir():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _applied_versions(cur) -> set[str]:
    cur.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def apply_migrations(max_attempts: int = 30, delay_seconds: float = 1.0) -> None:
    files = _migration_files()
    for attempt in range(1, max_attempts + 1):
        try:
            with db_cursor() as (conn, cur):
                cur.execute(_SCHEMA_MIGRATIONS_DDL)
                applied = _applied_versions(cur)
                for path in files:
                    version = path.name
                    if version in applied:
                        continue
                    sql = path.read_text(encoding="utf-8")
                    logger.info("Applying migration %s", version)
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)",
                        (version,),
                    )
                conn.commit()
            logger.info("Schema migrations complete (%s files).", len(files))
            return
        except psycopg2.OperationalError:
            if attempt >= max_attempts:
                raise
            logger.warning(
                "Database unavailable for migrations; retrying (%s/%s).",
                attempt,
                max_attempts,
            )
            time.sleep(delay_seconds)


def ensure_schema(max_attempts: int = 30, delay_seconds: float = 1.0) -> None:
    """Backward-compatible entry point used by application startup."""
    apply_migrations(max_attempts=max_attempts, delay_seconds=delay_seconds)
