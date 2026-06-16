from typing import Optional

from fastapi import APIRouter, HTTPException

from ...db import get_db_connection
from ...services.pagination import build_paginated_response, paginate_query
from ...types import OptionalUuidStr, UuidStr
from ._deps import AuditRead
from ._shared import _promotion_audit_row_to_item

router = APIRouter(dependencies=[AuditRead])

@router.get("/ui/promotion_audit")
def search_promotion_audit(
    tenant_id: OptionalUuidStr = None,
    q: Optional[str] = None,
    page: int = 1,
    size: int = 10,
):
    conn = None
    try:
        conn = get_db_connection()
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
        items = [_promotion_audit_row_to_item(row) for row in rows]
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


def _promotion_audit_row_to_item(row) -> dict:
    return {
        "id": str(row[0]),
        "tenant_id": str(row[1]),
        "resource_type": row[2],
        "resource_id": str(row[3]),
        "resource_name": row[4],
        "actor_id": row[5],
        "promotion_reason": row[6],
        "action": row[7],
        "source": row[8],
        "created_at": row[9].isoformat() if row[9] else None,
    }


@router.get("/ui/promotion_audit/{promotion_id}")
def get_promotion_audit(promotion_id: UuidStr, tenant_id: OptionalUuidStr = None):
    conn = None
    try:
        conn = get_db_connection()
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
        return _promotion_audit_row_to_item(row)
    finally:
        if conn:
            conn.close()
