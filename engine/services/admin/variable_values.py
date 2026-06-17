"""Signal variable value CRUD for admin UI."""

import uuid

from fastapi import HTTPException

from ...db import get_db_connection
from ...models import VariableValueCreateUpdate
from ...services.admin_responses import admin_mutation
from ...services.pagination import (
    build_paginated_response,
    clamp_pagination,
    paginate_query,
)
from ...types import UuidStr
from .common import get_signal_tenant_id


def create_variable_value(payload: VariableValueCreateUpdate) -> dict:
    conn = get_db_connection()
    try:
        new_id = str(uuid.uuid4())
        cur = conn.cursor()
        get_signal_tenant_id(cur, payload.signal_id)
        cur.execute(
            """
            INSERT INTO signal_variable_values (id, signal_id, name, value)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (signal_id, name) DO UPDATE
               SET value = EXCLUDED.value,
                   updated_at = NOW()
            RETURNING id
            """,
            (new_id, payload.signal_id, payload.name, payload.value),
        )
        row_id = str(cur.fetchone()[0])
        conn.commit()
        return admin_mutation("created", row_id)
    finally:
        conn.close()


def list_signal_variable_values(
    signal_id: UuidStr,
    *,
    page: int = 1,
    size: int = 10,
) -> dict:
    page, size = clamp_pagination(page, size)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        get_signal_tenant_id(cur, signal_id)
        base_query = """
            SELECT id, signal_id, name, value
              FROM signal_variable_values
             WHERE signal_id = %s
             ORDER BY name ASC, id ASC
        """
        total, rows, page, size = paginate_query(cur, base_query, (signal_id,), page, size)
        items = [
            {
                "id": str(row[0]),
                "signal_id": str(row[1]),
                "name": row[2],
                "value": row[3],
            }
            for row in rows
        ]
        return build_paginated_response(items, total, page, size)
    finally:
        conn.close()


def get_variable_value_item(variable_value_id: UuidStr) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, signal_id, name, value
              FROM signal_variable_values
             WHERE id = %s
            """,
            (variable_value_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Variable value not found.")
        return {
            "id": str(row[0]),
            "signal_id": str(row[1]),
            "name": row[2],
            "value": row[3],
        }
    finally:
        conn.close()


def update_variable_value(
    variable_value_id: UuidStr,
    payload: VariableValueCreateUpdate,
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT signal_id FROM signal_variable_values WHERE id = %s",
            (variable_value_id,),
        )
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Variable value not found.")
        existing_signal_id = str(existing[0])
        if existing_signal_id != payload.signal_id:
            existing_tenant = get_signal_tenant_id(cur, existing_signal_id)
            new_tenant = get_signal_tenant_id(cur, payload.signal_id)
            if existing_tenant != new_tenant:
                raise HTTPException(
                    status_code=422,
                    detail="Variable value cannot move across tenants.",
                )
        else:
            get_signal_tenant_id(cur, payload.signal_id)
        cur.execute(
            """
            UPDATE signal_variable_values
               SET signal_id = %s,
                   name = %s,
                   value = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (
                payload.signal_id,
                payload.name,
                payload.value,
                variable_value_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Variable value not found.")
        conn.commit()
        return admin_mutation("updated", variable_value_id)
    finally:
        conn.close()


def delete_variable_value(variable_value_id: UuidStr) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM signal_variable_values WHERE id = %s", (variable_value_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Variable value not found.")
        conn.commit()
        return admin_mutation("deleted", variable_value_id)
    finally:
        conn.close()
