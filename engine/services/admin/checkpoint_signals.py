"""Checkpoint-signal association CRUD for admin UI."""

import uuid

from fastapi import HTTPException

from ...db import get_db_connection
from ...models import CheckpointSignalCreateUpdate
from ...services.admin_responses import admin_mutation
from ...services.pagination import (
    MAX_PAGE_SIZE,
    build_paginated_response,
    paginate_query,
)
from ...types import OptionalUuidStr, UuidStr
from .common import collect_all_pages


def _validate_checkpoint_signal_association(cur, checkpoint_id: str, signal_id: str) -> None:
    cur.execute("SELECT tenant_id FROM checkpoints WHERE id = %s", (checkpoint_id,))
    checkpoint = cur.fetchone()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found.")
    cur.execute("SELECT tenant_id, name FROM signals WHERE id = %s", (signal_id,))
    signal = cur.fetchone()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found.")
    if str(checkpoint[0]) != str(signal[0]):
        raise HTTPException(
            status_code=422,
            detail="Checkpoint and signal must belong to the same tenant.",
        )
    cur.execute(
        """
        SELECT 1
          FROM checkpoint_signals cs
          JOIN signals existing ON existing.id = cs.signal_id
          JOIN signals incoming ON incoming.id = %s
         WHERE cs.checkpoint_id = %s
           AND existing.name = incoming.name
        """,
        (signal_id, checkpoint_id),
    )
    if cur.fetchone():
        raise HTTPException(
            status_code=409,
            detail="Checkpoint already links a signal with this name.",
        )


def create_checkpoint_signal(payload: CheckpointSignalCreateUpdate) -> dict:
    conn = get_db_connection()
    try:
        new_id = str(uuid.uuid4())
        cur = conn.cursor()
        _validate_checkpoint_signal_association(
            cur, payload.checkpoint_id, payload.signal_id
        )
        cur.execute(
            """
            INSERT INTO checkpoint_signals
            (id, checkpoint_id, signal_id)
            VALUES (%s, %s, %s)
            """,
            (new_id, payload.checkpoint_id, payload.signal_id),
        )
        conn.commit()
        return admin_mutation(
            "created",
            new_id,
            checkpoint_id=payload.checkpoint_id,
            signal_id=payload.signal_id,
        )
    finally:
        conn.close()


def delete_checkpoint_signal(checkpoint_signal_id: UuidStr) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM checkpoint_signals WHERE id = %s", (checkpoint_signal_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Checkpoint-signal link not found.")
        conn.commit()
        return admin_mutation("deleted", checkpoint_signal_id)
    finally:
        conn.close()


def list_checkpoint_signals(
    *,
    page: int = 1,
    size: int = 10,
    scoped_tenant_id: OptionalUuidStr = None,
    checkpoint_id: OptionalUuidStr = None,
    signal_id: OptionalUuidStr = None,
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        base_query = """
            SELECT cs.id, cs.checkpoint_id, cs.signal_id,
                   c.name as checkpoint_name, s.name as signal_name
              FROM checkpoint_signals cs
              JOIN checkpoints c ON cs.checkpoint_id = c.id
              JOIN signals s ON cs.signal_id = s.id
        """
        where_parts = []
        params: list = []
        if scoped_tenant_id:
            where_parts.append("c.tenant_id = %s")
            params.append(scoped_tenant_id)
        if checkpoint_id:
            where_parts.append("cs.checkpoint_id = %s")
            params.append(checkpoint_id)
        if signal_id:
            where_parts.append("cs.signal_id = %s")
            params.append(signal_id)
        if where_parts:
            base_query += " WHERE " + " AND ".join(where_parts)
        base_query += " ORDER BY c.name ASC, s.name ASC, cs.id ASC"
        total, rows, page, size = paginate_query(cur, base_query, tuple(params), page, size)
        items = [
            {
                "id": str(r[0]),
                "checkpoint_id": str(r[1]),
                "signal_id": str(r[2]),
                "checkpoint_name": r[3],
                "signal_name": r[4],
            }
            for r in rows
        ]
        return build_paginated_response(items, total, page, size)
    finally:
        conn.close()


def list_all_checkpoint_signals(
    *,
    scoped_tenant_id: OptionalUuidStr = None,
    checkpoint_id: OptionalUuidStr = None,
    signal_id: OptionalUuidStr = None,
) -> list:
    return collect_all_pages(
        lambda page: list_checkpoint_signals(
            page=page,
            size=MAX_PAGE_SIZE,
            scoped_tenant_id=scoped_tenant_id,
            checkpoint_id=checkpoint_id,
            signal_id=signal_id,
        )
    )
