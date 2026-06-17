"""Prove demo seed SQL re-applies cleanly against an already-seeded database."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from engine.db import get_db_connection

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA_SQL = ROOT / "sql" / "02_sample_data.sql"

pytestmark = pytest.mark.skipif(
    os.environ.get("DB_HOST", "localhost") == "localhost"
    and not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres (set DB_HOST or RUN_INTEGRATION_TESTS=1)",
)


def _seed_statements() -> list[str]:
    chunks: list[str] = []
    buffer: list[str] = []
    for line in SAMPLE_DATA_SQL.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("\\"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            buffer = []
            if statement:
                chunks.append(statement)
    if buffer:
        trailing = "\n".join(buffer).strip()
        if trailing:
            chunks.append(trailing)
    return chunks


def _apply_sample_data_sql() -> None:
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    try:
        for statement in _seed_statements():
            cur.execute(statement)
    finally:
        cur.close()
        conn.close()


def test_sample_data_sql_reapplies_without_error() -> None:
    _apply_sample_data_sql()
    _apply_sample_data_sql()
