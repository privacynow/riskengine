"""Promotion audit read queries."""

from typing import Optional

from fastapi import HTTPException

from ...auth import AuthContext, assert_admin_tenant_access
from ...db import get_db_connection
from ...services.pagination import build_paginated_response, paginate_query
from ...types import OptionalUuidStr, UuidStr
from .common import promotion_audit_row_to_item


def search_promotion_audit(
    *,
    tenant_id: OptionalUuidStr = None,
    q: Optional[str] = None,
    action: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    auth: AuthContext | None = None,
) -> dict:
    if tenant_id and auth is not None:
        assert_admin_tenant_access(auth, tenant_id)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        base_query = """
            SELECT id, tenant_id, resource_type, resource_id, resource_name,
                   actor_id, promotion_reason, action, source, created_at
              FROM promotion_audit
             WHERE 1=1
        """
        params: list[object] = []
        if tenant_id:
            base_query += " AND tenant_id = %s"
            params.append(tenant_id)
        if action:
            base_query += " AND action = %s"
            params.append(action)
        if q:
            like = f"%{q}%"
            base_query += """
                AND (
                    resource_name ILIKE %s
                    OR promotion_reason ILIKE %s
                    OR actor_id ILIKE %s
                    OR resource_type ILIKE %s
                )
            """
            params.extend([like, like, like, like])
        base_query += " ORDER BY created_at DESC, id ASC"

        total, rows, page, size = paginate_query(cur, base_query, params, page, size)
        items = [promotion_audit_row_to_item(row) for row in rows]
        return build_paginated_response(items, total, page, size)
    finally:
        conn.close()


def get_promotion_audit(
    promotion_id: UuidStr,
    *,
    tenant_id: OptionalUuidStr = None,
    auth: AuthContext | None = None,
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, tenant_id, resource_type, resource_id, resource_name,
                   actor_id, promotion_reason, action, source, created_at
              FROM promotion_audit
             WHERE id = %s
            """,
            (promotion_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Promotion audit record not found.")
        if tenant_id and str(row[1]) != tenant_id:
            raise HTTPException(status_code=404, detail="Promotion audit record not found.")
        if auth is not None:
            assert_admin_tenant_access(auth, str(row[1]))
        return promotion_audit_row_to_item(row)
    finally:
        conn.close()
