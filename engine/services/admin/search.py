"""Admin search queries across tenants, checkpoints, signals, and decisions."""

from typing import Optional

from ...db import get_db_connection
from ...services.pagination import build_paginated_response, paginate_query
from ...services.signal_log_search import search_signal_logs as search_signal_logs_service
from ...types import OptionalUuidStr
from .common import admin_signal_item_from_row


def search_tenants(*, q: str, page: int = 1, size: int = 10) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        like = f"%{q}%"
        base_query = """
            SELECT id, name
              FROM tenants
             WHERE name ILIKE %s
                OR id::text ILIKE %s
        """
        params = (like, like)
        total, rows, page, size = paginate_query(cur, base_query, params, page, size)
        items = [{"id": str(r[0]), "name": r[1]} for r in rows]
        return build_paginated_response(items, total, page, size)
    finally:
        conn.close()


def search_checkpoints(
    *,
    q: str,
    scoped_tenant_id: OptionalUuidStr = None,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        like = f"%{q}%"
        base_query = """
            SELECT c.id, c.tenant_id, c.name, c.description, c.type, c.dsl_expression,
                   CASE WHEN cv.checkpoint_id IS NOT NULL THEN true ELSE false END as is_current_version,
                   EXISTS (
                       SELECT 1
                         FROM checkpoint_current_version cvn
                        WHERE cvn.tenant_id = c.tenant_id
                          AND cvn.name = c.name
                   ) as name_has_current_version
              FROM checkpoints c
              LEFT JOIN checkpoint_current_version cv ON cv.checkpoint_id = c.id
             WHERE (c.name ILIKE %s
                OR c.id::text ILIKE %s
                OR c.type ILIKE %s
                OR c.description ILIKE %s
                OR c.dsl_expression ILIKE %s
                OR c.method_of_call ILIKE %s)
        """
        params = [like, like, like, like, like, like]

        if scoped_tenant_id:
            base_query += " AND c.tenant_id = %s"
            params.append(scoped_tenant_id)

        if active_only:
            base_query += " AND cv.checkpoint_id IS NOT NULL"

        base_query += " ORDER BY c.name ASC, c.id ASC"

        total, rows, page, size = paginate_query(cur, base_query, params, page, size)
        items = []
        for r in rows:
            items.append({
                "id": str(r[0]),
                "tenant_id": str(r[1]),
                "name": r[2],
                "description": r[3],
                "type": r[4],
                "dsl_expression": r[5],
                "is_current_version": r[6],
                "name_has_current_version": r[7],
            })
        return build_paginated_response(items, total, page, size)
    finally:
        conn.close()


def search_signals(
    *,
    q: str,
    scoped_tenant_id: OptionalUuidStr = None,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        like = f"%{q}%"
        base_query = """
            SELECT s.id, s.tenant_id, s.name, s.description, s.type, s.method_of_call,
                   s.expression_body, s.cost, s.cache_expiration_seconds, s.timeout_seconds,
                   s.can_run_in_parallel, s.order_of_evaluation, s.http_method,
                   s.request_url_params_template, s.request_body_template,
                   s.request_headers_template, s.bearer_token, s.allow_caching,
                   s.global_reuse, s.function_params_template,
                   CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version,
                   EXISTS (
                       SELECT 1
                         FROM signal_current_version scvn
                        WHERE scvn.tenant_id = s.tenant_id
                          AND scvn.name = s.name
                   ) as name_has_current_version
              FROM signals s
              LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
             WHERE (s.name ILIKE %s
                OR s.id::text ILIKE %s
                OR s.type ILIKE %s
                OR s.description ILIKE %s
                OR s.method_of_call ILIKE %s)
        """
        params = [like, like, like, like, like]

        if scoped_tenant_id:
            base_query += " AND s.tenant_id = %s"
            params.append(scoped_tenant_id)

        if active_only:
            base_query += " AND scv.signal_id IS NOT NULL"

        base_query += " ORDER BY s.name ASC, s.id ASC"

        total, rows, page, size = paginate_query(cur, base_query, params, page, size)
        items = [admin_signal_item_from_row(r, include_current=True) for r in rows]
        return build_paginated_response(items, total, page, size)
    finally:
        conn.close()


def search_decisions(
    *,
    q: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    scoped_tenant_id: OptionalUuidStr = None,
    page: int = 1,
    size: int = 10,
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        base_query = """
            SELECT dl.id, dl.checkpoint_id, dl.tenant_id, dl.applicant_id,
                   dl.final_decision_value, dl.cost_incurred, dl.correlation_id,
                   dl.decision_timestamp, c.name AS checkpoint_name
              FROM decision_log dl
         LEFT JOIN checkpoints c ON c.id = dl.checkpoint_id
         LEFT JOIN signal_log sl ON dl.id = sl.decision_log_id
             WHERE 1=1
        """
        conditions = []
        params = []

        if q:
            like = f"%{q}%"
            conditions.append(
                """
                (
                  dl.final_decision_value ILIKE %s
                  OR dl.correlation_id ILIKE %s
                  OR dl.applicant_id ILIKE %s
                  OR dl.checkpoint_id::text ILIKE %s
                  OR c.name ILIKE %s
                  OR sl.signal_value ILIKE %s
                )
                """
            )
            params.extend([like, like, like, like, like, like])

        if from_date:
            conditions.append("dl.decision_timestamp >= %s")
            params.append(from_date)
        if to_date:
            conditions.append("dl.decision_timestamp <= %s")
            params.append(to_date)

        if scoped_tenant_id:
            conditions.append("dl.tenant_id = %s")
            params.append(scoped_tenant_id)

        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        base_query += " GROUP BY dl.id, c.name"

        total, rows, page, size = paginate_query(cur, base_query, params, page, size)
        items = []
        for r in rows:
            items.append(
                {
                    "id": str(r[0]),
                    "checkpoint_id": str(r[1]),
                    "tenant_id": str(r[2]),
                    "applicant_id": r[3],
                    "final_decision_value": r[4],
                    "cost_incurred": r[5],
                    "correlation_id": r[6],
                    "decision_timestamp": r[7].isoformat() if r[7] else None,
                    "checkpoint_name": r[8],
                }
            )
        return build_paginated_response(items, total, page, size)
    finally:
        conn.close()


def search_signal_logs(
    *,
    q: Optional[str] = None,
    scoped_tenant_id: OptionalUuidStr = None,
    failures_only: bool = False,
    param_name: Optional[str] = None,
    param_value: Optional[str] = None,
    page: int = 1,
    size: int = 10,
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        return search_signal_logs_service(
            cur,
            q=q,
            tenant_id=scoped_tenant_id,
            failures_only=failures_only,
            param_name=param_name,
            param_value=param_value,
            page=page,
            size=size,
        )
    finally:
        conn.close()
