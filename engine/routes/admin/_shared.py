from fastapi import HTTPException

from ...config import logger
from ...models import SignalCreateUpdate
from ...services.security import (
    admin_signal_secret_fields,
    contains_embedded_credential,
    has_bearer_token_value,
    redact_template_for_response,
)
from ...services.secret_storage import SecretEncryptionNotConfiguredError, encrypt_secret
from ...services.templates import extract_placeholders_from_text

GENERIC_ADMIN_ERROR = "An internal error occurred."


def raise_admin_error(exc: Exception, *, context: str) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, SecretEncryptionNotConfiguredError):
        logger.error("%s: %s", context, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    logger.exception("%s", context)
    raise HTTPException(status_code=500, detail=GENERIC_ADMIN_ERROR) from exc


def _collect_all_pages(fetch_page):
    items = []
    page = 1
    while True:
        result = fetch_page(page)
        page_items = result["items"]
        items.extend(page_items)
        if not page_items or len(items) >= result["total"]:
            return items
        page += 1


def _get_signal_tenant_id(cur, signal_id: str) -> str:
    cur.execute("SELECT tenant_id FROM signals WHERE id = %s", (signal_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return str(row[0])


def _assert_checkpoint_tenant(cur, checkpoint_id: str, tenant_id: str) -> None:
    cur.execute("SELECT tenant_id FROM checkpoints WHERE id = %s", (checkpoint_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found.")
    if str(row[0]) != tenant_id:
        raise HTTPException(
            status_code=422,
            detail="Checkpoint does not belong to the requested tenant.",
        )


def _validate_signal_templates(payload: SignalCreateUpdate) -> None:
    checks = (
        ("request_headers_template", payload.request_headers_template),
        ("request_body_template", payload.request_body_template),
        ("request_url_params_template", payload.request_url_params_template),
        ("function_params_template", payload.function_params_template),
    )
    for field_name, value in checks:
        if contains_embedded_credential(value):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{field_name} must not embed credentials; "
                    "store outbound auth in bearer_token only."
                ),
            )


def _signal_placeholders_from_row(r) -> list:
    placeholders = extract_placeholders_from_text(r[13]) \
        + extract_placeholders_from_text(r[14]) \
        + extract_placeholders_from_text(r[15]) \
        + extract_placeholders_from_text(r[19])
    return sorted(set(placeholders))


def _admin_signal_item_from_row(r, *, include_current: bool) -> dict:
    item = {
        "id": str(r[0]),
        "tenant_id": str(r[1]),
        "name": r[2],
        "description": r[3],
        "type": r[4],
        "method_of_call": r[5],
        "expression_body": r[6],
        "cost": r[7],
        "cache_expiration_seconds": r[8],
        "timeout_seconds": r[9],
        "can_run_in_parallel": r[10],
        "order_of_evaluation": r[11],
        "http_method": r[12],
        "request_url_params_template": redact_template_for_response(r[13]),
        "request_body_template": redact_template_for_response(r[14]),
        "request_headers_template": redact_template_for_response(r[15]),
        **admin_signal_secret_fields(r[16]),
        "allow_caching": r[17],
        "global_reuse": r[18],
        "function_params_template": redact_template_for_response(r[19]),
        "param_placeholders": _signal_placeholders_from_row(r),
    }
    if include_current:
        item["is_current_version"] = r[20]
        item["name_has_current_version"] = r[21]
    return item


def _resolve_signal_bearer_token(cur, payload: SignalCreateUpdate) -> str | None:
    if has_bearer_token_value(payload.bearer_token):
        return encrypt_secret(payload.bearer_token.strip())
    cur.execute(
        """
        SELECT bearer_token
          FROM signals
         WHERE tenant_id = %s AND name = %s
         ORDER BY updated_at DESC
         LIMIT 1
        """,
        (payload.tenant_id, payload.name),
    )
    row = cur.fetchone()
    return row[0] if row else None

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
