import uuid

from fastapi import APIRouter, HTTPException

from ...db import get_db_connection
from ...models import VariableValueCreateUpdate
from ...services.admin_responses import admin_mutation
from ...services.pagination import (
    build_paginated_response,
    clamp_pagination,
    paginate_query,
)
from ...types import UuidStr
from ._deps import AdminRead, AdminWrite
from ._shared import _get_signal_tenant_id

router = APIRouter()

@router.post("/ui/variable_values", dependencies=[AdminWrite])
def create_variable_value(payload: VariableValueCreateUpdate):
    """Create or update a row in signal_variable_values for a variable signal."""
    conn = None
    try:
        new_id = str(uuid.uuid4())
        conn = get_db_connection()
        cur = conn.cursor()
        _get_signal_tenant_id(cur, payload.signal_id)
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
        if conn:
            conn.close()


@router.get("/ui/signals/{signal_id}/variable_values", dependencies=[AdminRead])
def list_signal_variable_values(signal_id: UuidStr, page: int = 1, size: int = 10):
    """List stored variable values for a variable-type signal."""
    page, size = clamp_pagination(page, size)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        _get_signal_tenant_id(cur, signal_id)
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
        if conn:
            conn.close()


@router.get("/ui/variable_values/{variable_value_id}", dependencies=[AdminRead])
def get_variable_value_item(variable_value_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
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
        if conn:
            conn.close()


@router.put("/ui/variable_values/{variable_value_id}", dependencies=[AdminWrite])
def update_variable_value(variable_value_id: UuidStr, payload: VariableValueCreateUpdate):
    conn = None
    try:
        conn = get_db_connection()
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
            existing_tenant = _get_signal_tenant_id(cur, existing_signal_id)
            new_tenant = _get_signal_tenant_id(cur, payload.signal_id)
            if existing_tenant != new_tenant:
                raise HTTPException(
                    status_code=422,
                    detail="Variable value cannot move across tenants.",
                )
        else:
            _get_signal_tenant_id(cur, payload.signal_id)
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
        if conn:
            conn.close()


@router.delete("/ui/variable_values/{variable_value_id}", dependencies=[AdminWrite])
def delete_variable_value(variable_value_id: UuidStr):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM signal_variable_values WHERE id = %s", (variable_value_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Variable value not found.")
        conn.commit()
        return admin_mutation("deleted", variable_value_id)
    finally:
        if conn:
            conn.close()
