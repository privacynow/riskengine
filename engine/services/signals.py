import json
import random
import uuid
from typing import Any, Dict, Optional

import httpx

from ..db import db_cursor
from .dsl import evaluate_expression
from .security import validate_outbound_signal_url
from .templates import parse_headers_string, parse_params_string, render_template


def coerce_signal_value(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        stripped = val.strip()
        lowered = stripped.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        try:
            if "." in stripped:
                return float(stripped)
            return int(stripped)
        except ValueError:
            return stripped
    return val


def load_stored_variable_value(signal_id: str, var_name: Optional[str]) -> Optional[Any]:
    with db_cursor() as (_, cur):
        if var_name:
            cur.execute(
                """
                SELECT value FROM signal_variable_values
                 WHERE signal_id = %s AND name = %s
                 ORDER BY updated_at DESC
                 LIMIT 1
                """,
                (signal_id, var_name),
            )
        else:
            cur.execute(
                """
                SELECT value FROM signal_variable_values
                 WHERE signal_id = %s
                 ORDER BY updated_at DESC
                 LIMIT 1
                """,
                (signal_id,),
            )
        row = cur.fetchone()
        if not row:
            return None
        return coerce_signal_value(row[0])


def store_variable_signal_value(signal_id: str, var_name: str, var_value: Any):
    with db_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT id FROM signal_variable_values
             WHERE signal_id = %s AND name = %s
            """,
            (signal_id, var_name),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                INSERT INTO signal_variable_values (id, signal_id, name, value)
                VALUES (%s, %s, %s, %s)
                """,
                (str(uuid.uuid4()), signal_id, var_name, str(var_value)),
            )
        else:
            cur.execute(
                """
                UPDATE signal_variable_values
                   SET value = %s, updated_at = NOW()
                 WHERE id = %s
                """,
                (str(var_value), row[0]),
            )
        conn.commit()


def income_verification(params: Dict[str, Any]) -> bool:
    try:
        min_income = int(params.get("min_income", "30000"))
    except (TypeError, ValueError):
        min_income = 30000
    return random.randint(10000, 80000) >= min_income


def loan_amount_check(params: Dict[str, Any]) -> int:
    try:
        max_loan = int(params.get("max_loan", "50000"))
    except (TypeError, ValueError):
        max_loan = 50000
    return random.randint(1000, max_loan + 1000)


def disbursement_limit_check(params: Dict[str, Any]) -> bool:
    return random.random() < 0.7


def local_function_map(name: str, params: Dict[str, Any]) -> Any:
    if name == "income_verification":
        return income_verification(params)
    if name == "loan_amount_check":
        return loan_amount_check(params)
    if name == "disbursement_limit_check":
        return disbursement_limit_check(params)
    raise ValueError(f"Unknown local function: {name}")


async def invoke_signal(
    signal_type: str,
    method_of_call: str,
    expression_body: Optional[str],
    invoke_context: Dict[str, Any],
    http_method: Optional[str],
    url_params_template: Optional[str],
    body_template: Optional[str],
    headers_template: Optional[str],
    bearer_token: Optional[str],
    function_params_template: Optional[str],
    signal_id: str,
    timeout_seconds: int = 30,
) -> Any:
    if signal_type in ("internal_endpoint", "external_endpoint"):
        final_method = (http_method or "GET").upper()
        url = method_of_call or ""
        if not url:
            return None
        validate_outbound_signal_url(url)
        rendered_url_params = render_template(url_params_template or "", invoke_context)
        params_dict = parse_params_string(rendered_url_params)
        rendered_headers = render_template(headers_template or "", invoke_context)
        headers_dict = parse_headers_string(rendered_headers)
        if bearer_token:
            headers_dict["Authorization"] = f"Bearer {bearer_token}"
        rendered_body = render_template(body_template or "", invoke_context)
        body_data = None
        if rendered_body and rendered_body.strip():
            try:
                body_data = json.loads(rendered_body)
            except json.JSONDecodeError:
                body_data = rendered_body

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            request_kwargs = {
                "params": params_dict,
                "headers": headers_dict,
            }
            if final_method == "GET":
                resp = await client.get(url, **request_kwargs)
            elif final_method == "POST":
                resp = await client.post(
                    url,
                    **request_kwargs,
                    json=body_data if isinstance(body_data, dict) else None,
                    data=None if isinstance(body_data, dict) else body_data,
                )
            elif final_method == "PUT":
                resp = await client.put(
                    url,
                    **request_kwargs,
                    json=body_data if isinstance(body_data, dict) else None,
                    data=None if isinstance(body_data, dict) else body_data,
                )
            elif final_method == "PATCH":
                resp = await client.patch(
                    url,
                    **request_kwargs,
                    json=body_data if isinstance(body_data, dict) else None,
                    data=None if isinstance(body_data, dict) else body_data,
                )
            elif final_method == "DELETE":
                resp = await client.delete(url, **request_kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {final_method}")

            resp.raise_for_status()
            try:
                payload = resp.json()
                if isinstance(payload, dict) and "value" in payload:
                    return coerce_signal_value(payload["value"])
                return payload
            except (json.JSONDecodeError, ValueError):
                return True

    if signal_type == "function":
        rendered_params = render_template(function_params_template or "", invoke_context)
        try:
            params_obj = json.loads(rendered_params) if rendered_params.strip() else {}
        except json.JSONDecodeError:
            params_obj = {}
        return local_function_map(method_of_call, params_obj)

    if signal_type == "expression":
        return evaluate_expression(expression_body or "", invoke_context)

    if signal_type == "variable":
        var_name = method_of_call.strip() if method_of_call else None
        value = load_stored_variable_value(signal_id, var_name)
        if value is None and var_name:
            value = invoke_context.get(var_name)
        value = coerce_signal_value(value)
        store_name = var_name or "value"
        if value is not None:
            store_variable_signal_value(signal_id, store_name, value)
        return value

    raise ValueError(f"Unknown signal type: {signal_type}")
