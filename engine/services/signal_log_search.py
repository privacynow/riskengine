"""SQL-level signal log search and pagination."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from .pagination import clamp_pagination
from .security import redact_param_map_for_response


def _build_filters(
    *,
    q: Optional[str],
    tenant_id: Optional[str],
    failures_only: bool,
    param_name: Optional[str],
    param_value: Optional[str],
) -> tuple[str, list[Any]]:
    conditions = ["1=1"]
    params: list[Any] = []

    if tenant_id:
        conditions.append("dl.tenant_id = %s")
        params.append(tenant_id)

    if failures_only:
        conditions.append("sl.success = false")

    if q:
        like = f"%{q}%"
        conditions.append(
            """
            (
              sl.signal_id::text ILIKE %s
              OR sl.applicant_id ILIKE %s
              OR sl.decision_log_id::text ILIKE %s
              OR sl.signal_value ILIKE %s
              OR CAST(sl.cost_incurred AS text) ILIKE %s
              OR CAST(sl.success AS text) ILIKE %s
              OR sl.id::text ILIKE %s
              OR sig.name ILIKE %s
              OR slv.param_name ILIKE %s
              OR slv.param_value ILIKE %s
            )
            """
        )
        params.extend([like] * 10)

    if param_name:
        conditions.append("slv.param_name ILIKE %s")
        params.append(f"%{param_name}%")

    if param_value:
        conditions.append("slv.param_value ILIKE %s")
        params.append(f"%{param_value}%")

    return " AND ".join(conditions), params


def search_signal_logs(
    cur,
    *,
    q: Optional[str] = None,
    tenant_id: Optional[str] = None,
    failures_only: bool = False,
    param_name: Optional[str] = None,
    param_value: Optional[str] = None,
    page: int = 1,
    size: int = 10,
) -> dict[str, Any]:
    page, size = clamp_pagination(page, size)
    where_sql, params = _build_filters(
        q=q,
        tenant_id=tenant_id,
        failures_only=failures_only,
        param_name=param_name,
        param_value=param_value,
    )

    matched_cte = f"""
        WITH matched AS (
            SELECT DISTINCT sl.id, sl.started_at
              FROM signal_log sl
         LEFT JOIN signals sig ON sig.id = sl.signal_id
         LEFT JOIN decision_log dl ON dl.id = sl.decision_log_id
         LEFT JOIN signal_log_values slv ON sl.id = slv.signal_log_id
             WHERE {where_sql}
        )
    """

    cur.execute(f"{matched_cte} SELECT COUNT(*) FROM matched", params)
    total = cur.fetchone()[0]

    offset = (page - 1) * size
    cur.execute(
        f"""
        {matched_cte},
        paged AS (
            SELECT id, started_at
              FROM matched
          ORDER BY started_at DESC, id
             LIMIT %s OFFSET %s
        )
        SELECT sl.id,
               sl.decision_log_id,
               sl.signal_id,
               sl.applicant_id,
               sl.signal_value,
               sl.started_at,
               sl.completed_at,
               sl.cost_incurred,
               sl.success,
               sl.error_message,
               sig.name AS signal_name,
               slv.param_name,
               slv.param_value
          FROM paged p
          JOIN signal_log sl ON sl.id = p.id
     LEFT JOIN signals sig ON sig.id = sl.signal_id
     LEFT JOIN signal_log_values slv ON sl.id = slv.signal_log_id
      ORDER BY p.started_at DESC, sl.id, slv.param_name
        """,
        [*params, size, offset],
    )
    joined_rows = cur.fetchall()

    log_map: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "id": None,
            "decision_log_id": None,
            "signal_id": None,
            "signal_name": None,
            "applicant_id": None,
            "signal_value": None,
            "started_at": None,
            "completed_at": None,
            "cost_incurred": None,
            "success": None,
            "error_message": None,
            "param_values": [],
        }
    )

    for row in joined_rows:
        sl_id = str(row[0])
        if log_map[sl_id]["id"] is None:
            log_map[sl_id].update(
                {
                    "id": sl_id,
                    "decision_log_id": str(row[1]),
                    "signal_id": str(row[2]),
                    "applicant_id": row[3],
                    "signal_value": row[4],
                    "started_at": row[5].isoformat() if row[5] else None,
                    "completed_at": row[6].isoformat() if row[6] else None,
                    "cost_incurred": row[7],
                    "success": row[8],
                    "error_message": row[9],
                    "signal_name": row[10],
                }
            )
        param_name_value = row[11]
        param_val = row[12]
        if param_name_value is not None:
            log_map[sl_id]["param_values"].append(
                {"param_name": param_name_value, "param_value": param_val}
            )

    items = []
    for log in log_map.values():
        raw_map = {
            item["param_name"]: item["param_value"]
            for item in log["param_values"]
            if item.get("param_name") is not None
        }
        redacted_map = redact_param_map_for_response(raw_map)
        log["param_values"] = [
            {"param_name": name, "param_value": value}
            for name, value in redacted_map.items()
        ]
        items.append(log)

    return {"items": items, "total": total, "page": page, "size": size}
