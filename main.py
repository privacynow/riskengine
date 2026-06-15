import os
import uuid
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
import re
import json
import random  # used for sample local functions
import math

import psycopg2
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from simpleeval import SimpleEval
from fastapi.staticfiles import StaticFiles

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(asctime)s] %(name)s - %(message)s"
)
logger = logging.getLogger("risk-engine")

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "risk_engine_db")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


# -----------------------------------------------------------------------------
# Pydantic Models
# -----------------------------------------------------------------------------
class DecisionRequest(BaseModel):
    checkpoint_name: str
    applicant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class DecisionResponse(BaseModel):
    decision_id: str
    final_decision_value: str
    cost_incurred: int
    signal_results: Dict[str, Any]


class TenantCreateUpdate(BaseModel):
    name: str
    copyFromTenantId: Optional[str] = None


class CheckpointCreateUpdate(BaseModel):
    tenant_id: str
    name: str
    description: Optional[str] = None
    type: str
    dsl_expression: str
    method_of_call: Optional[str] = None
    max_cost: int = 0
    override_cost_flag: bool = False
    timeout_seconds: int = 30
    makeCurrentVersion: bool = False


class SignalCreateUpdate(BaseModel):
    tenant_id: str
    name: str
    description: Optional[str] = None
    type: str
    method_of_call: Optional[str] = None
    expression_body: Optional[str] = None
    cost: int = 0
    cache_expiration_seconds: int = 0
    timeout_seconds: int = 30
    can_run_in_parallel: bool = False
    order_of_evaluation: int = 1
    http_method: Optional[str] = None
    request_url_params_template: Optional[str] = None
    request_body_template: Optional[str] = None
    request_headers_template: Optional[str] = None
    bearer_token: Optional[str] = None
    allow_caching: bool = False
    global_reuse: bool = False
    function_params_template: Optional[str] = None
    makeCurrentVersion: bool = False


class VariableValueCreateUpdate(BaseModel):
    signal_id: str
    name: str
    value: Optional[str] = None


class CheckpointSignalCreateUpdate(BaseModel):
    checkpoint_id: str
    signal_id: str


# -----------------------------------------------------------------------------
# In-Memory Cache
# -----------------------------------------------------------------------------
class InMemorySignalCache:
    def __init__(self):
        self.cache = OrderedDict()
        self.max_size = 1000

    def make_key(self, tenant_id: str, checkpoint_id: str, applicant_id: Optional[str], signal_id: str):
        return (tenant_id, checkpoint_id, applicant_id or "", signal_id)

    def get(self, tenant_id: str, checkpoint_id: str, applicant_id: Optional[str], signal_id: str):
        key = self.make_key(tenant_id, checkpoint_id, applicant_id, signal_id)
        if key not in self.cache:
            return None
        value, expires_ts = self.cache[key]
        if time.time() > expires_ts:
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return value

    def set(self, tenant_id: str, checkpoint_id: str, applicant_id: Optional[str], signal_id: str, value: Any, ttl: int):
        key = self.make_key(tenant_id, checkpoint_id, applicant_id, signal_id)
        expires_ts = time.time() + ttl
        self.cache[key] = (value, expires_ts)
        self.cache.move_to_end(key)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)


in_memory_signal_cache = InMemorySignalCache()

# -----------------------------------------------------------------------------
# Async Logging for signal_log
# -----------------------------------------------------------------------------
log_queue = asyncio.Queue()


def _process_audit_logging(log_item: Dict[str, Any]):
    """
    Inserts the signal_log row and the param placeholders into signal_log_values.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if log_item["type"] == "signal":
            # Insert into signal_log (one row per-signal invocation)
            cur.execute("""
                INSERT INTO signal_log
                (id, decision_log_id, signal_id, applicant_id,
                 signal_value, started_at, completed_at,
                 cost_incurred, success)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                log_item["signal_log_id"],
                log_item["decision_log_id"],
                log_item["signal_id"],
                log_item["applicant_id"],
                log_item["signal_value"],
                log_item["started_at"],
                log_item["completed_at"],
                log_item["cost_incurred"],
                log_item["success"]
            ))

            # Insert param placeholders into signal_log_values
            placeholder_values = log_item.get("placeholder_values", {})
            for param_name, param_value in placeholder_values.items():
                row_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO signal_log_values
                    (id, signal_log_id, param_name, param_value)
                    VALUES (%s, %s, %s, %s)
                """, (
                    row_id,
                    log_item["signal_log_id"],
                    param_name,
                    str(param_value)
                ))

        conn.commit()
        cur.close()
    finally:
        if conn:
            conn.close()


async def log_processor():
    while True:
        item = await log_queue.get()
        if item is None:
            break
        try:
            _process_audit_logging(item)
        except Exception as e:
            logger.error("Error processing audit log: %s", e)
        finally:
            log_queue.task_done()


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(title="Risk/Decision Engine + UI")


@app.get("/")
def root_redirect():
    return RedirectResponse(url="/admin/index.html")


# Demo mock endpoints used by sample internal/external signal URLs.
MOCK_ENDPOINT_RESPONSES = {
    "doc-verify": {"value": True},
    "sanction-screen": {"value": True},
    "kyc_score": {"value": 85},
    "credit_score": {"value": 75},
    "onboarding": {"value": True},
    "compliance": {"value": True},
    "underwriting": {"value": True},
    "disbursement": {"value": True},
    "servicing": {"value": True},
}


@app.api_route("/mock/{mock_name}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def mock_service(mock_name: str):
    payload = MOCK_ENDPOINT_RESPONSES.get(mock_name, {"value": True})
    return payload


app.mount("/admin", StaticFiles(directory="ui", html=True), name="admin")


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(log_processor())
    logger.info("Risk engine started.")


@app.on_event("shutdown")
async def on_shutdown():
    await log_queue.put(None)
    await log_queue.join()
    logger.info("Risk engine shutdown.")


# -----------------------------------------------------------------------------
# Pagination Helpers
# -----------------------------------------------------------------------------
def build_paginated_response(items, total, page, size):
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size
    }


def paginate_query(cur, query, params, page: int, size: int):
    count_query = f"SELECT COUNT(*) FROM ({query}) as sub"
    cur.execute(count_query, params)
    total = cur.fetchone()[0]
    offset = (page - 1) * size
    paged_query = query + f" LIMIT {size} OFFSET {offset}"
    cur.execute(paged_query, params)
    rows = cur.fetchall()
    return total, rows


# -----------------------------------------------------------------------------
# Template/Placeholder Helpers
# -----------------------------------------------------------------------------
def extract_placeholders_from_text(template_str: Optional[str]) -> List[str]:
    if not template_str:
        return []
    pattern = r"%([^%]+)%"
    matches = re.findall(pattern, template_str)
    placeholders = set(m.strip() for m in matches)
    return sorted(placeholders)


def render_template(template_str: str, context: Dict[str, Any]) -> str:
    if not template_str:
        return template_str
    pattern = r"%([^%]+)%"
    out = template_str
    matches = re.findall(pattern, template_str)
    for match in matches:
        key = match.strip()
        token = f"%{key}%"
        if key in context:
            out = out.replace(token, str(context[key]))
        else:
            # If placeholder not in context, replace with empty
            out = out.replace(token, "")
    return out


def parse_params_string(params_str: str) -> Dict[str, str]:
    result = {}
    if not params_str or not params_str.strip():
        return result
    parts = params_str.split("&")
    for kv_pair in parts:
        kv_pair = kv_pair.strip()
        if "=" not in kv_pair:
            continue
        key, val = kv_pair.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def parse_headers_string(headers_str: str) -> Dict[str, str]:
    headers = {}
    if not headers_str:
        return headers
    for line in headers_str.split("\n"):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
    return headers


# -----------------------------------------------------------------------------
# Local Function Implementations (for "function" signals)
# -----------------------------------------------------------------------------
def income_verification(params: Dict[str, Any]) -> bool:
    min_income_str = params.get("min_income", "30000")
    try:
        min_income = int(min_income_str)
    except:
        min_income = 30000
    user_income = random.randint(10000, 80000)
    return (user_income >= min_income)


def loan_amount_check(params: Dict[str, Any]) -> int:
    max_loan_str = params.get("max_loan", "50000")
    try:
        max_loan = int(max_loan_str)
    except:
        max_loan = 50000
    return random.randint(1000, max_loan + 1000)


def disbursement_limit_check(params: Dict[str, Any]) -> bool:
    limit_str = params.get("limit", "100000")
    try:
        _limit_val = int(limit_str)
    except:
        _limit_val = 100000
    # For demonstration, random ~70% chance of True
    return (random.random() < 0.7)


def local_function_map(name: str, params: Dict[str, Any]) -> Any:
    if name == "income_verification":
        return income_verification(params)
    elif name == "loan_amount_check":
        return loan_amount_check(params)
    elif name == "disbursement_limit_check":
        return disbursement_limit_check(params)
    else:
        raise ValueError(f"Unknown local function: {name}")


# -----------------------------------------------------------------------------
# Utility functions for variable signals and value coercion
# -----------------------------------------------------------------------------
def coerce_signal_value(val: Any) -> Any:
    """Convert stored/string signal values into Python types for DSL evaluation."""
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
    """
    Read the configured value for a variable signal from signal_variable_values.
    Falls back to the first stored row for the signal when name is absent.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
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
    finally:
        if conn:
            conn.close()


def store_variable_signal_value(signal_id: str, var_name: str, var_value: Any):
    """
    Insert or update the final 'variable' signal value into signal_variable_values table.
    This is optional but demonstrates how we might store a global or last-known value.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # We'll do an upsert by checking first if there's a row with that signal_id & name
        cur.execute("""
            SELECT id FROM signal_variable_values
             WHERE signal_id = %s AND name = %s
        """, (signal_id, var_name))
        row = cur.fetchone()
        if not row:
            row_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO signal_variable_values
                (id, signal_id, name, value)
                VALUES (%s, %s, %s, %s)
            """, (row_id, signal_id, var_name, str(var_value)))
        else:
            existing_id = row[0]
            cur.execute("""
                UPDATE signal_variable_values
                   SET value = %s,
                       updated_at = NOW()
                 WHERE id = %s
            """, (str(var_value), existing_id))

        conn.commit()
        cur.close()
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# Signal Invocation
# -----------------------------------------------------------------------------
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
    tenant_id: str,
    function_params_template: Optional[str],
    signal_id: str
) -> Any:
    """
    Invokes a signal by its type. If 'variable', we store the final value in signal_variable_values.
    """
    if signal_type in ("internal_endpoint", "external_endpoint"):
        final_method = (http_method or "GET").upper()
        url = method_of_call or ""
        if not url:
            return None
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
            except:
                # If not valid JSON, treat as raw text
                body_data = rendered_body

        async with httpx.AsyncClient(timeout=5) as client:
            if final_method == "GET":
                resp = await client.get(url, params=params_dict, headers=headers_dict)
            elif final_method == "POST":
                resp = await client.post(
                    url,
                    params=params_dict,
                    headers=headers_dict,
                    json=body_data if isinstance(body_data, dict) else None,
                    data=None if isinstance(body_data, dict) else body_data
                )
            elif final_method == "PUT":
                resp = await client.put(
                    url,
                    params=params_dict,
                    headers=headers_dict,
                    json=body_data if isinstance(body_data, dict) else None,
                    data=None if isinstance(body_data, dict) else body_data
                )
            elif final_method == "PATCH":
                resp = await client.patch(
                    url,
                    params=params_dict,
                    headers=headers_dict,
                    json=body_data if isinstance(body_data, dict) else None,
                    data=None if isinstance(body_data, dict) else body_data
                )
            elif final_method == "DELETE":
                resp = await client.delete(url, params=params_dict, headers=headers_dict)
            else:
                raise ValueError(f"Unsupported HTTP method: {final_method}")

            resp.raise_for_status()
            try:
                j = resp.json()
                if "value" in j:
                    return coerce_signal_value(j["value"])
                return j
            except:
                return True

    elif signal_type == "function":
        rendered_params = render_template(function_params_template or "", invoke_context)
        try:
            params_obj = json.loads(rendered_params) if rendered_params.strip() else {}
        except:
            params_obj = {}
        return local_function_map(method_of_call, params_obj)

    elif signal_type == "expression":
        se = SimpleEval()
        se.names = invoke_context
        return se.eval(expression_body or "")

    elif signal_type == "variable":
        var_name = (method_of_call.strip() if method_of_call else None)
        value = load_stored_variable_value(signal_id, var_name)
        if value is None and var_name:
            value = invoke_context.get(var_name)
        value = coerce_signal_value(value)
        store_name = var_name or "value"
        if value is not None:
            store_variable_signal_value(signal_id, store_name, value)
        return value

    else:
        raise ValueError(f"Unknown signal type: {signal_type}")


# -----------------------------------------------------------------------------
# Decorators / Explanation Builders
# -----------------------------------------------------------------------------
def decorate_dsl_expression(dsl_expression: str, signal_map: Dict[str, Any]) -> str:
    """
    Given the DSL expression (e.g. "age_check and credit_score > 80")
    and a dict of {signal_name: signal_value}, produce a string with
    each signal replaced by "signal_name (signal_value)".
    """
    # We'll do a safe replacement by word boundary. We'll sort by length descending to avoid partial collisions.
    # e.g., if we have "credit" and "credit_score" we'd want to replace "credit_score" first.
    sorted_signals = sorted(signal_map.keys(), key=len, reverse=True)

    result = dsl_expression
    for sig_name in sorted_signals:
        val_str = str(signal_map[sig_name])
        # Use a regex with word boundaries
        pattern = r"\b" + re.escape(sig_name) + r"\b"
        replacement = f"{sig_name} ({val_str})"
        result = re.sub(pattern, replacement, result)
    return result


def build_template_explanation(template_str: Optional[str], param_map: Dict[str, Any]) -> str:
    """
    Returns a string showing placeholders replaced with "key (value)".
    For example:
      "userId=%applicant_id%" => "userId=applicant_id (1234)"
    """
    if not template_str:
        return ""

    out = template_str
    pattern = r"%([^%]+)%"
    matches = re.findall(pattern, template_str)
    for match in matches:
        key = match.strip()
        token = f"%{key}%"
        val = param_map.get(key, "")
        # New format: key (val)
        sub = f"{val}"
        out = out.replace(token, sub)
    return out

# -----------------------------------------------------------------------------
# Public Endpoints
# -----------------------------------------------------------------------------
@app.get("/checkpoints/{checkpoint_name}")
def get_checkpoint_details(checkpoint_name: str):
    """
    Return checkpoint by name + associated signals.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # checkpoint
        cur.execute("""
            SELECT c.id, c.tenant_id, c.name, c.description, c.type,
                   c.dsl_expression, c.method_of_call, c.max_cost,
                   c.override_cost_flag, c.timeout_seconds
            FROM checkpoints c
            WHERE c.name = %s
        """, (checkpoint_name,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
        cp_data = {
            "id": str(row[0]),
            "tenant_id": str(row[1]),
            "name": row[2],
            "description": row[3],
            "type": row[4],
            "dsl_expression": row[5],
            "method_of_call": row[6],
            "max_cost": row[7],
            "override_cost_flag": row[8],
            "timeout_seconds": row[9]
        }

        # signals
        cur.execute("""
            SELECT s.id, s.tenant_id, s.name, s.description, s.type,
                   s.method_of_call, s.expression_body, s.cost,
                   s.cache_expiration_seconds, s.timeout_seconds,
                   s.can_run_in_parallel, s.order_of_evaluation,
                   s.http_method, s.request_url_params_template,
                   s.request_body_template, s.request_headers_template,
                   s.bearer_token, s.allow_caching, s.global_reuse,
                   s.function_params_template
            FROM signals s
            JOIN checkpoint_signals cs ON cs.signal_id = s.id
            JOIN checkpoints c ON c.id = cs.checkpoint_id
            WHERE c.name = %s
            ORDER BY s.order_of_evaluation
        """, (checkpoint_name,))
        sig_rows = cur.fetchall()
        signals_data = []
        for srow in sig_rows:
            placeholders = extract_placeholders_from_text(srow[13]) \
                + extract_placeholders_from_text(srow[14]) \
                + extract_placeholders_from_text(srow[15]) \
                + extract_placeholders_from_text(srow[19])
            placeholders = sorted(set(placeholders))
            signals_data.append({
                "id": str(srow[0]),
                "tenant_id": str(srow[1]),
                "name": srow[2],
                "description": srow[3],
                "type": srow[4],
                "method_of_call": srow[5],
                "expression_body": srow[6],
                "cost": srow[7],
                "cache_expiration_seconds": srow[8],
                "timeout_seconds": srow[9],
                "can_run_in_parallel": srow[10],
                "order_of_evaluation": srow[11],
                "http_method": srow[12],
                "request_url_params_template": srow[13],
                "request_body_template": srow[14],
                "request_headers_template": srow[15],
                "bearer_token": srow[16],
                "allow_caching": srow[17],
                "global_reuse": srow[18],
                "function_params_template": srow[19],
                "param_placeholders": placeholders
            })

        cp_data["signals"] = signals_data
        return cp_data

    finally:
        if conn:
            conn.close()


@app.get("/signals/{signal_name}")
def get_signal_details(signal_name: str):
    """
    Return a single signal by name.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, tenant_id, name, description, type, method_of_call,
                   expression_body, cost, cache_expiration_seconds, timeout_seconds,
                   can_run_in_parallel, order_of_evaluation, http_method,
                   request_url_params_template, request_body_template,
                   request_headers_template, bearer_token, allow_caching,
                   global_reuse, function_params_template
            FROM signals
            WHERE name = %s
        """, (signal_name,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Signal not found.")

        placeholders = extract_placeholders_from_text(row[13]) \
            + extract_placeholders_from_text(row[14]) \
            + extract_placeholders_from_text(row[15]) \
            + extract_placeholders_from_text(row[19])
        placeholders = sorted(set(placeholders))

        return {
            "id": str(row[0]),
            "tenant_id": str(row[1]),
            "name": row[2],
            "description": row[3],
            "type": row[4],
            "method_of_call": row[5],
            "expression_body": row[6],
            "cost": row[7],
            "cache_expiration_seconds": row[8],
            "timeout_seconds": row[9],
            "can_run_in_parallel": row[10],
            "order_of_evaluation": row[11],
            "http_method": row[12],
            "request_url_params_template": row[13],
            "request_body_template": row[14],
            "request_headers_template": row[15],
            "bearer_token": row[16],
            "allow_caching": row[17],
            "global_reuse": row[18],
            "function_params_template": row[19],
            "param_placeholders": placeholders
        }
    finally:
        if conn:
            conn.close()


@app.get("/decisions/{decision_id}")
def get_historical_decision(decision_id: str):
    """
    Returns the decision_log row plus expanded signal details, checkpoint DSL,
    decorated DSL, and template param renderings.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1) decision_log row
        cur.execute("""
            SELECT id, checkpoint_id, tenant_id, applicant_id,
                   final_decision_value, cost_incurred,
                   correlation_id, decision_timestamp
            FROM decision_log
            WHERE id = %s
        """, (decision_id,))
        drow = cur.fetchone()
        if not drow:
            raise HTTPException(status_code=404, detail="Decision not found.")

        decision_data = {
            "id": str(drow[0]),
            "checkpoint_id": str(drow[1]),
            "tenant_id": str(drow[2]),
            "applicant_id": drow[3],
            "final_decision_value": drow[4],
            "cost_incurred": drow[5],
            "correlation_id": drow[6],
            "decision_timestamp": drow[7]
        }

        # 2) fetch the checkpoint's name + DSL expression
        cp_id = drow[1]
        cur.execute("""
            SELECT name, dsl_expression
            FROM checkpoints
            WHERE id = %s
        """, (cp_id,))
        crow = cur.fetchone()
        checkpoint_name = crow[0] if crow else None
        checkpoint_dsl = crow[1] if crow else None
        decision_data["checkpoint_name"] = checkpoint_name
        decision_data["checkpoint_dsl_expression"] = checkpoint_dsl

        # 3) gather all signal_log rows
        cur.execute("""
            SELECT id, signal_id, applicant_id, signal_value,
                   started_at, completed_at, cost_incurred, success
            FROM signal_log
            WHERE decision_log_id = %s
        """, (decision_id,))
        srows = cur.fetchall()

        signal_name_value_map = {}  # for DSL decoration
        signal_details_list = []

        # 4) For each signal_log, fetch signal info + param values
        for s in srows:
            sl_id = str(s[0])
            sig_id = str(s[1])
            s_applicant = s[2]
            s_value = s[3]
            s_started = s[4]
            s_completed = s[5]
            s_cost = s[6]
            s_success = s[7]

            # fetch param values
            cur2 = conn.cursor()
            cur2.execute("""
                SELECT param_name, param_value
                FROM signal_log_values
                WHERE signal_log_id = %s
            """, (sl_id,))
            param_rows = cur2.fetchall()
            param_map = {pr[0]: pr[1] for pr in param_rows}
            cur2.close()

            # fetch signal's main fields
            cur3 = conn.cursor()
            cur3.execute("""
                SELECT name, method_of_call, request_url_params_template,
                       request_body_template, request_headers_template,
                       function_params_template, type
                FROM signals
                WHERE id = %s
            """, (sig_id,))
            sinfo = cur3.fetchone()
            cur3.close()

            if sinfo:
                sig_name = sinfo[0]
                sig_method = sinfo[1]
                sig_url_tmpl = sinfo[2]
                sig_body_tmpl = sinfo[3]
                sig_headers_tmpl = sinfo[4]
                sig_func_tmpl = sinfo[5]
                sig_type = sinfo[6]
            else:
                # fallback if missing
                sig_name = "(unknown)"
                sig_method = ""
                sig_url_tmpl = ""
                sig_body_tmpl = ""
                sig_headers_tmpl = ""
                sig_func_tmpl = ""
                sig_type = "unknown"

            # add to name->value map for DSL
            signal_name_value_map[sig_name] = s_value

            # build "rendered explanation" for each template
            url_explanation = build_template_explanation(sig_url_tmpl, param_map)
            body_explanation = build_template_explanation(sig_body_tmpl, param_map)
            headers_explanation = build_template_explanation(sig_headers_tmpl, param_map)
            func_explanation = build_template_explanation(sig_func_tmpl, param_map)

            signal_details_list.append({
                "signal_log_id": sl_id,
                "signal_id": sig_id,
                "signal_name": sig_name,
                "signal_type": sig_type,
                "signal_value": s_value,
                "started_at": s_started,
                "completed_at": s_completed,
                "cost_incurred": s_cost,
                "success": s_success,
                "param_values": param_map,  # raw param key->val
                "original_templates": {
                    "request_url_params_template": sig_url_tmpl,
                    "request_body_template": sig_body_tmpl,
                    "request_headers_template": sig_headers_tmpl,
                    "function_params_template": sig_func_tmpl
                },
                "rendered_explanations": {
                    "url_params": url_explanation,
                    "body": body_explanation,
                    "headers": headers_explanation,
                    "function_params": func_explanation
                },
                "method_of_call": sig_method
            })

        decision_data["signals"] = signal_details_list

        # 5) Create a "decorated_dsl_expression" if checkpoint_dsl
        if checkpoint_dsl:
            decorated = decorate_dsl_expression(checkpoint_dsl, signal_name_value_map)
            decision_data["decorated_dsl_expression"] = decorated
        else:
            decision_data["decorated_dsl_expression"] = None

        return decision_data

    finally:
        if conn:
            conn.close()


@app.post("/decisions", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest):
    """
    Main endpoint: Evaluate the checkpoint (by name) and log results.
    We only insert one row in decision_log, and one row per-signal in signal_log.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1) Find checkpoint
        cur.execute("""
            SELECT id, tenant_id, dsl_expression, max_cost, override_cost_flag
            FROM checkpoints
            WHERE name = %s
        """, (request.checkpoint_name,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")

        checkpoint_id = str(row[0])
        tenant_id = str(row[1])
        dsl_expression = row[2]
        max_cost = row[3]
        override_cost_flag = row[4]

        # 2) Insert into decision_log once
        decision_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO decision_log
            (id, checkpoint_id, tenant_id, applicant_id,
             final_decision_value, cost_incurred, correlation_id, decision_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            decision_id,
            checkpoint_id,
            tenant_id,
            request.applicant_id,
            "PENDING",
            0,
            request.correlation_id,
            datetime.utcnow()
        ))
        conn.commit()

        # 3) Grab signals for this checkpoint
        cur.execute("""
            SELECT s.id, s.name, s.type, s.method_of_call, s.expression_body,
                   s.cost, s.cache_expiration_seconds, s.timeout_seconds,
                   s.can_run_in_parallel, s.order_of_evaluation,
                   s.http_method, s.request_url_params_template,
                   s.request_body_template, s.request_headers_template,
                   s.bearer_token, s.allow_caching, s.global_reuse,
                   s.function_params_template
            FROM signals s
            JOIN checkpoint_signals cs ON cs.signal_id = s.id
            WHERE cs.checkpoint_id = %s
            ORDER BY s.order_of_evaluation
        """, (checkpoint_id,))
        signals = cur.fetchall()

        total_cost = 0
        signal_results = {}
        user_params = request.parameters or {}

        # Group signals by order_of_evaluation
        signals_by_order = defaultdict(list)
        for sdat in signals:
            order_eval = sdat[9]  # s.order_of_evaluation
            signals_by_order[order_eval].append(sdat)

        # 4) Evaluate signals in ascending order
        for order_val in sorted(signals_by_order.keys()):
            tasks = []
            for srow in signals_by_order[order_val]:
                # Pull out columns from srow
                (sig_id, sig_name, sig_type, sig_method, sig_expr,
                 sig_cost, sig_cache_exp, sig_timeout, sig_can_parallel,
                 sig_order_eval, sig_http_method, sig_url_tmpl,
                 sig_body_tmpl, sig_headers_tmpl, sig_bearer,
                 sig_allowcache, sig_globalreuse, sig_func_params) = srow

                # If cost limit is not overridden, skip if this would exceed max_cost
                if not override_cost_flag and (total_cost + sig_cost) > max_cost:
                    signal_results[sig_name] = False
                    continue

                async def run_signal(
                    row_sig_id=sig_id,
                    row_sig_name=sig_name,
                    row_sig_type=sig_type,
                    row_sig_method=sig_method,
                    row_sig_expr=sig_expr,
                    row_sig_cost=sig_cost,
                    row_sig_cache_exp=sig_cache_exp,
                    row_sig_timeout=sig_timeout,
                    row_sig_can_parallel=sig_can_parallel,
                    row_sig_http_method=sig_http_method,
                    row_sig_url_tmpl=sig_url_tmpl,
                    row_sig_body_tmpl=sig_body_tmpl,
                    row_sig_headers_tmpl=sig_headers_tmpl,
                    row_sig_bearer=sig_bearer,
                    row_sig_allowcache=sig_allowcache,
                    row_sig_globalreuse=sig_globalreuse,
                    row_sig_func_params=sig_func_params
                ):
                    started = datetime.utcnow()
                    success = True
                    value = None

                    # Collect placeholders for this particular signal
                    placeholders_list = set()
                    for tmpl in [
                        row_sig_url_tmpl, row_sig_body_tmpl, row_sig_headers_tmpl, row_sig_func_params
                    ]:
                        placeholders_list.update(extract_placeholders_from_text(tmpl or ""))
                    placeholders_list = sorted(placeholders_list)

                    partial_params = {}
                    for p in placeholders_list:
                        if p in user_params:
                            partial_params[p] = user_params[p]

                    # Combine with previous signals' results
                    context = dict(signal_results)
                    context.update(partial_params)

                    # 1) Check the in-memory or DB cache if allow_caching == True
                    applicant_key = None if row_sig_globalreuse else request.applicant_id
                    if row_sig_allowcache:
                        cached_val = in_memory_signal_cache.get(
                            tenant_id, checkpoint_id, applicant_key, row_sig_id
                        )
                        if cached_val is not None:
                            value = coerce_signal_value(cached_val)
                        else:
                            # check DB
                            cur2 = conn.cursor()
                            cur2.execute("""
                                SELECT signal_value, expires_at
                                  FROM signal_cached_values
                                 WHERE tenant_id = %s
                                   AND checkpoint_id = %s
                                   AND signal_id = %s
                                   AND (
                                     (applicant_id IS NULL AND %s IS NULL)
                                     OR (applicant_id = %s)
                                   )
                            """, (
                                tenant_id,
                                checkpoint_id,
                                row_sig_id,
                                applicant_key,
                                applicant_key
                            ))
                            crow = cur2.fetchone()
                            if crow:
                                val_str, expires_at = crow
                                if datetime.utcnow() < expires_at:
                                    value = coerce_signal_value(val_str)
                                    in_memory_signal_cache.set(
                                        tenant_id, checkpoint_id,
                                        applicant_key, row_sig_id,
                                        val_str, row_sig_cache_exp
                                    )
                            cur2.close()

                    # 2) If not cached, invoke signal
                    if value is None:
                        try:
                            value = await invoke_signal(
                                signal_type=row_sig_type,
                                method_of_call=row_sig_method,
                                expression_body=row_sig_expr,
                                invoke_context=context,
                                http_method=row_sig_http_method,
                                url_params_template=row_sig_url_tmpl,
                                body_template=row_sig_body_tmpl,
                                headers_template=row_sig_headers_tmpl,
                                bearer_token=row_sig_bearer,
                                tenant_id=tenant_id,
                                function_params_template=row_sig_func_params,
                                signal_id=row_sig_id
                            )
                        except Exception as e:
                            logger.error("Error invoking signal %s: %s", row_sig_name, e)
                            success = False
                            value = False

                        # 3) If success and allow_caching, store in cache
                        if row_sig_allowcache and success:
                            in_memory_signal_cache.set(
                                tenant_id, checkpoint_id, applicant_key, row_sig_id, value, row_sig_cache_exp
                            )
                            cur3 = conn.cursor()
                            expires_at = datetime.utcnow() + timedelta(seconds=row_sig_cache_exp)
                            val_str = str(value)
                            # Upsert pattern in DB
                            cur3.execute("""
                                INSERT INTO signal_cached_values
                                (id, tenant_id, checkpoint_id, signal_id, applicant_id, signal_value, expires_at)
                                VALUES (uuid_generate_v4(), %s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                tenant_id, checkpoint_id, row_sig_id,
                                applicant_key, val_str, expires_at
                            ))
                            cur3.execute("""
                                UPDATE signal_cached_values
                                   SET signal_value = %s,
                                       expires_at = %s,
                                       updated_at = NOW()
                                 WHERE tenant_id = %s
                                   AND checkpoint_id = %s
                                   AND signal_id = %s
                                   AND (
                                     (applicant_id IS NULL AND %s IS NULL)
                                     OR (applicant_id = %s)
                                   )
                            """, (
                                val_str, expires_at,
                                tenant_id, checkpoint_id, row_sig_id,
                                applicant_key, applicant_key
                            ))
                            conn.commit()

                    ended = datetime.utcnow()

                    # 4) Write to log queue
                    log_id = str(uuid.uuid4())
                    await log_queue.put({
                        "type": "signal",
                        "signal_log_id": log_id,
                        "decision_log_id": decision_id,
                        "signal_id": row_sig_id,
                        "applicant_id": request.applicant_id,
                        "signal_value": str(value),
                        "started_at": started,
                        "completed_at": ended,
                        "cost_incurred": row_sig_cost if success else 0,
                        "success": success,
                        "placeholder_values": partial_params
                    })

                    return (row_sig_name, value, row_sig_cost if success else 0)

                # Append that task
                tasks.append(run_signal())

            # Wait for all tasks at this order_of_evaluation
            results = await asyncio.gather(*tasks)

            # Add results to signal_results, accumulate cost
            for (n, v, c) in results:
                signal_results[n] = coerce_signal_value(v)
                total_cost += c

        # 5) Evaluate DSL expression using final results
        final_eval = False
        try:
            se = SimpleEval()
            se.names = signal_results
            final_eval = se.eval(dsl_expression)
        except Exception as e:
            logger.error("Error evaluating DSL expression: %s", e)
            final_eval = False

        final_decision_val = str(final_eval)

        # 6) Update decision_log with final result
        cur.execute("""
            UPDATE decision_log
               SET final_decision_value = %s,
                   cost_incurred = %s,
                   updated_at = NOW()
             WHERE id = %s
        """, (final_decision_val, total_cost, decision_id))
        conn.commit()

        return DecisionResponse(
            decision_id=decision_id,
            final_decision_value=final_decision_val,
            cost_incurred=total_cost,
            signal_results=signal_results
        )

    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# Admin UI Endpoints (/ui/...)
# -----------------------------------------------------------------------------

# (Unchanged UI routes omitted for brevity - all remain as in original code)
# FULL code below includes them for completeness.

@app.post("/ui/tenants")
def create_tenant(payload: TenantCreateUpdate):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create new tenant
        cur.execute(
            "INSERT INTO tenants (name) VALUES (%s) RETURNING id",
            (payload.name,)
        )
        new_tenant_id = cur.fetchone()[0]
        
        # If copying from existing tenant
        if payload.copyFromTenantId:
            # Copy only active checkpoints
            cur.execute("""
                INSERT INTO checkpoints (
                    tenant_id, name, description, type, dsl_expression,
                    method_of_call, max_cost, override_cost_flag, timeout_seconds
                )
                SELECT %s, c.name, c.description, c.type, c.dsl_expression,
                       c.method_of_call, c.max_cost, c.override_cost_flag, c.timeout_seconds
                FROM checkpoints c
                INNER JOIN checkpoint_current_version cv 
                    ON c.id = cv.checkpoint_id 
                    AND c.tenant_id = cv.tenant_id
                WHERE c.tenant_id = %s
                RETURNING id, name
            """, (new_tenant_id, payload.copyFromTenantId))
            
            checkpoint_mappings = {}
            for row in cur.fetchall():
                checkpoint_mappings[row[0]] = row[0]  # Using the new checkpoint id
            
            # Set current versions for the copied checkpoints
            for old_id, new_cp_id in checkpoint_mappings.items():
                cur.execute("""
                    INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
                    SELECT %s, name, %s FROM checkpoints WHERE id = %s
                """, (new_tenant_id, new_cp_id, old_id))
            
            # Copy only active signals
            cur.execute("""
                INSERT INTO signals (
                    tenant_id, name, description, type, method_of_call,
                    expression_body, cost, cache_expiration_seconds, timeout_seconds,
                    can_run_in_parallel, order_of_evaluation, http_method,
                    request_url_params_template, request_body_template,
                    request_headers_template, bearer_token, allow_caching,
                    global_reuse, function_params_template
                )
                SELECT %s, s.name, s.description, s.type, s.method_of_call,
                       s.expression_body, s.cost, s.cache_expiration_seconds, s.timeout_seconds,
                       s.can_run_in_parallel, s.order_of_evaluation, s.http_method,
                       s.request_url_params_template, s.request_body_template,
                       s.request_headers_template, s.bearer_token, s.allow_caching,
                       s.global_reuse, s.function_params_template
                FROM signals s
                INNER JOIN signal_current_version cv 
                    ON s.id = cv.signal_id 
                    AND s.tenant_id = cv.tenant_id
                WHERE s.tenant_id = %s
                RETURNING id, name
            """, (new_tenant_id, payload.copyFromTenantId))
            
            signal_mappings = {}
            for row in cur.fetchall():
                signal_mappings[row[0]] = row[0]  # Using the new signal id
            
            # Set current versions for the copied signals
            for old_id, new_sig_id in signal_mappings.items():
                cur.execute("""
                    INSERT INTO signal_current_version (tenant_id, name, signal_id)
                    SELECT %s, name, %s FROM signals WHERE id = %s
                """, (new_tenant_id, new_sig_id, old_id))
            
            # Copy checkpoint-signal associations only for active checkpoints and signals
            for old_cp_id, new_cp_id in checkpoint_mappings.items():
                for old_sig_id, new_sig_id in signal_mappings.items():
                    cur.execute("""
                        INSERT INTO checkpoint_signals (checkpoint_id, signal_id)
                        SELECT %s, %s
                        WHERE EXISTS (
                            SELECT 1 FROM checkpoint_signals
                            WHERE checkpoint_id = %s AND signal_id = %s
                        )
                    """, (new_cp_id, new_sig_id, old_cp_id, old_sig_id))
            
            # Copy signal variable values for active signals
            for old_sig_id, new_sig_id in signal_mappings.items():
                cur.execute("""
                    INSERT INTO signal_variable_values (
                        signal_id, name, value
                    )
                    SELECT %s, name, value
                    FROM signal_variable_values
                    WHERE signal_id = %s
                """, (new_sig_id, old_sig_id))
        
        conn.commit()
        return {"id": new_tenant_id}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.post("/ui/checkpoints")
def create_checkpoint(payload: CheckpointCreateUpdate):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create new checkpoint version
        cur.execute("""
            INSERT INTO checkpoints (
                tenant_id, name, description, type, dsl_expression,
                method_of_call, max_cost, override_cost_flag, timeout_seconds
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            payload.tenant_id, payload.name, payload.description,
            payload.type, payload.dsl_expression, payload.method_of_call,
            payload.max_cost, payload.override_cost_flag, payload.timeout_seconds
        ))
        
        new_checkpoint_id = cur.fetchone()[0]
        
        # If this should be the current version
        if payload.makeCurrentVersion:
            cur.execute("""
                INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (tenant_id, name) DO UPDATE
                SET checkpoint_id = EXCLUDED.checkpoint_id,
                    updated_at = NOW()
            """, (payload.tenant_id, payload.name, new_checkpoint_id))
        
        conn.commit()
        return {"id": new_checkpoint_id}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.post("/ui/signals")
def create_signal(payload: SignalCreateUpdate):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create new signal version
        cur.execute("""
            INSERT INTO signals (
                tenant_id, name, description, type, method_of_call,
                expression_body, cost, cache_expiration_seconds, timeout_seconds,
                can_run_in_parallel, order_of_evaluation, http_method,
                request_url_params_template, request_body_template,
                request_headers_template, bearer_token, allow_caching,
                global_reuse, function_params_template
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            payload.tenant_id, payload.name, payload.description,
            payload.type, payload.method_of_call, payload.expression_body,
            payload.cost, payload.cache_expiration_seconds, payload.timeout_seconds,
            payload.can_run_in_parallel, payload.order_of_evaluation,
            payload.http_method, payload.request_url_params_template,
            payload.request_body_template, payload.request_headers_template,
            payload.bearer_token, payload.allow_caching,
            payload.global_reuse, payload.function_params_template
        ))
        
        new_signal_id = cur.fetchone()[0]
        
        # If this should be the current version
        if payload.makeCurrentVersion:
            # First update the signal's current version
            cur.execute("""
                INSERT INTO signal_current_version (tenant_id, name, signal_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (tenant_id, name) DO UPDATE
                SET signal_id = EXCLUDED.signal_id,
                    updated_at = NOW()
            """, (payload.tenant_id, payload.name, new_signal_id))
            
            # Then copy and update associated checkpoints
            cur.execute("""
                WITH RECURSIVE
                upstream_checkpoints AS (
                    -- Get directly associated checkpoints
                    SELECT DISTINCT c.id, c.tenant_id, c.name, c.description,
                           c.type, c.dsl_expression, c.method_of_call,
                           c.max_cost, c.override_cost_flag, c.timeout_seconds
                    FROM checkpoints c
                    JOIN checkpoint_signals cs ON c.id = cs.checkpoint_id
                    WHERE cs.signal_id = %s
                    
                    UNION
                    
                    -- Get checkpoints that reference this signal in expressions
                    SELECT DISTINCT c.id, c.tenant_id, c.name, c.description,
                           c.type, c.dsl_expression, c.method_of_call,
                           c.max_cost, c.override_cost_flag, c.timeout_seconds
                    FROM checkpoints c
                    WHERE c.dsl_expression LIKE '%%' || %s || '%%'
                )
                INSERT INTO checkpoints (
                    tenant_id, name, description, type, dsl_expression,
                    method_of_call, max_cost, override_cost_flag, timeout_seconds
                )
                SELECT tenant_id, name, description, type, dsl_expression,
                       method_of_call, max_cost, override_cost_flag, timeout_seconds
                FROM upstream_checkpoints
                RETURNING id, name
            """, (new_signal_id, payload.name))
            
            # Update checkpoint current versions
            checkpoint_updates = cur.fetchall()
            for new_cp_id, cp_name in checkpoint_updates:
                cur.execute("""
                    INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (tenant_id, name) DO UPDATE
                    SET checkpoint_id = EXCLUDED.checkpoint_id,
                        updated_at = NOW()
                """, (payload.tenant_id, cp_name, new_cp_id))
        
        conn.commit()
        return {"id": new_signal_id}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.get("/ui/tenants")
def list_tenants(page: int = 1, size: int = 10):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        base_query = "SELECT id, name FROM tenants"
        total, rows = paginate_query(cur, base_query, (), page, size)
        items = []
        for r in rows:
            items.append({"id": str(r[0]), "name": r[1]})
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@app.get("/ui/all_tenants")
def list_all_tenants():
    """Unpaginated tenant list for dropdowns and bulk admin views."""
    return list_tenants(page=1, size=10000)["items"]


@app.get("/ui/tenants/{tenant_id}")
def get_tenant(tenant_id: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM tenants WHERE id=%s", (tenant_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        return {"id": str(row[0]), "name": row[1]}
    finally:
        if conn:
            conn.close()


@app.put("/ui/tenants/{tenant_id}")
def update_tenant(tenant_id: str, payload: TenantCreateUpdate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE tenants
               SET name = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (payload.name, tenant_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        conn.commit()
        return {"id": tenant_id, "name": payload.name}
    finally:
        if conn:
            conn.close()


@app.delete("/ui/tenants/{tenant_id}")
def delete_tenant(tenant_id: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        conn.commit()
        return {"deleted": True, "id": tenant_id}
    finally:
        if conn:
            conn.close()


@app.get("/ui/checkpoints")
def list_checkpoints(tenant_id: Optional[str] = None, page: int = 1, size: int = 10, active_only: bool = False):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        base_query = """
            SELECT c.id, c.tenant_id, c.name, c.description, c.type, c.dsl_expression,
                   c.method_of_call, c.max_cost, c.override_cost_flag, c.timeout_seconds,
                   c.created_at, c.updated_at,
                   t.name as tenant_name,
                   COALESCE(
                       (SELECT json_agg(json_build_object(
                           'id', s.id,
                           'name', s.name,
                           'type', s.type,
                           'method_of_call', s.method_of_call,
                           'cost', s.cost,
                           'timeout_seconds', s.timeout_seconds
                       ))
                       FROM checkpoint_signals cs
                       JOIN signals s ON cs.signal_id = s.id
                       WHERE cs.checkpoint_id = c.id), '[]'
                   ) as signals,
                   CASE 
                       WHEN cv.checkpoint_id IS NOT NULL THEN true 
                       ELSE false 
                   END as is_current_version
            FROM checkpoints c
            LEFT JOIN tenants t ON c.tenant_id = t.id
            LEFT JOIN checkpoint_current_version cv ON cv.checkpoint_id = c.id
            """

        where_clause = []
        params = []

        if tenant_id:
            where_clause.append("c.tenant_id = %s")
            params.append(tenant_id)

        if active_only:
            where_clause.append("cv.checkpoint_id IS NOT NULL")

        if where_clause:
            base_query += " WHERE " + " AND ".join(where_clause)

        base_query += " ORDER BY c.created_at DESC"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({base_query}) as count_query"
        cur.execute(count_query, params)
        total = cur.fetchone()[0]

        # Get paginated results
        paginated_query = base_query + " LIMIT %s OFFSET %s"
        params.extend([size, (page - 1) * size])
        cur.execute(paginated_query, params)
        
        checkpoints = []
        for row in cur.fetchall():
            checkpoint = {
                "id": str(row[0]),
                "tenant_id": str(row[1]),
                "name": row[2],
                "description": row[3],
                "type": row[4],
                "dsl_expression": row[5],
                "method_of_call": row[6],
                "max_cost": row[7],
                "override_cost_flag": row[8],
                "timeout_seconds": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
                "updated_at": row[11].isoformat() if row[11] else None,
                "tenant_name": row[12],
                "signals": row[13],
                "is_current_version": row[14],
                "param_placeholders": extract_placeholders_from_text(row[5]) if row[5] else []
            }
            checkpoints.append(checkpoint)

        return {
            "items": checkpoints,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": (total + size - 1) // size
        }

    except Exception as e:
        logger.error(f"Error in list_checkpoints: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.get("/ui/all_checkpoints")
def list_all_checkpoints(
    tenant_id: Optional[str] = None,
    active_only: bool = False,
):
    """Unpaginated checkpoint list for dropdowns and bulk admin views."""
    return list_checkpoints(
        tenant_id=tenant_id,
        page=1,
        size=10000,
        active_only=active_only,
    )["items"]


@app.get("/ui/checkpoints/{checkpoint_id}")
def get_checkpoint(checkpoint_id: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, tenant_id, name, description, type, dsl_expression,
                   method_of_call, max_cost, override_cost_flag, timeout_seconds
              FROM checkpoints
             WHERE id = %s
            """,
            (checkpoint_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
        return {
            "id": str(row[0]),
            "tenant_id": str(row[1]),
            "name": row[2],
            "description": row[3],
            "type": row[4],
            "dsl_expression": row[5],
            "method_of_call": row[6],
            "max_cost": row[7],
            "override_cost_flag": row[8],
            "timeout_seconds": row[9],
        }
    finally:
        if conn:
            conn.close()


@app.put("/ui/checkpoints/{checkpoint_id}")
def update_checkpoint(checkpoint_id: str, payload: CheckpointCreateUpdate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE checkpoints
               SET tenant_id = %s,
                   name = %s,
                   description = %s,
                   type = %s,
                   dsl_expression = %s,
                   method_of_call = %s,
                   max_cost = %s,
                   override_cost_flag = %s,
                   timeout_seconds = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (
                payload.tenant_id,
                payload.name,
                payload.description,
                payload.type,
                payload.dsl_expression,
                payload.method_of_call,
                payload.max_cost,
                payload.override_cost_flag,
                payload.timeout_seconds,
                checkpoint_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
        conn.commit()
        return {"id": checkpoint_id, **payload.dict()}
    finally:
        if conn:
            conn.close()


@app.delete("/ui/checkpoints/{checkpoint_id}")
def delete_checkpoint(checkpoint_id: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM checkpoints WHERE id = %s", (checkpoint_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Checkpoint not found.")
        conn.commit()
        return {"deleted": True, "id": checkpoint_id}
    finally:
        if conn:
            conn.close()


@app.get("/ui/signals")
def list_signals(checkpoint_id: Optional[str] = None,
                 tenant_id: Optional[str] = None,
                 page: int = 1,
                 size: int = 10,
                 active_only: bool = False):
    """
    If checkpoint_id is provided, returns signals associated with that checkpoint.
    If tenant_id is provided, returns signals for that tenant.
    Otherwise returns all signals.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if checkpoint_id:
            base_query = """
                SELECT s.id, s.tenant_id, s.name, s.description, s.type,
                       s.method_of_call, s.expression_body, s.cost,
                       s.cache_expiration_seconds, s.timeout_seconds,
                       s.can_run_in_parallel, s.order_of_evaluation,
                       s.http_method, s.request_url_params_template,
                       s.request_body_template, s.request_headers_template,
                       s.bearer_token, s.allow_caching, s.global_reuse,
                       s.function_params_template,
                       CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version
                  FROM signals s
                  JOIN checkpoint_signals cs ON cs.signal_id = s.id
                  LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
                 WHERE cs.checkpoint_id = %s
            """
            params = [checkpoint_id]
            if active_only:
                base_query += " AND scv.signal_id IS NOT NULL"
        elif tenant_id:
            base_query = """
                SELECT s.id, s.tenant_id, s.name, s.description, s.type,
                       s.method_of_call, s.expression_body, s.cost,
                       s.cache_expiration_seconds, s.timeout_seconds,
                       s.can_run_in_parallel, s.order_of_evaluation,
                       s.http_method, s.request_url_params_template,
                       s.request_body_template, s.request_headers_template,
                       s.bearer_token, s.allow_caching, s.global_reuse,
                       s.function_params_template,
                       CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version
                  FROM signals s
                  LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
                 WHERE s.tenant_id = %s
            """
            params = [tenant_id]
            if active_only:
                base_query += " AND scv.signal_id IS NOT NULL"
        else:
            base_query = """
                SELECT s.id, s.tenant_id, s.name, s.description, s.type,
                       s.method_of_call, s.expression_body, s.cost,
                       s.cache_expiration_seconds, s.timeout_seconds,
                       s.can_run_in_parallel, s.order_of_evaluation,
                       s.http_method, s.request_url_params_template,
                       s.request_body_template, s.request_headers_template,
                       s.bearer_token, s.allow_caching, s.global_reuse,
                       s.function_params_template,
                       CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version
                  FROM signals s
                  LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
            """
            params = []
            if active_only:
                base_query += " WHERE scv.signal_id IS NOT NULL"

        total, rows = paginate_query(cur, base_query, params, page, size)
        items = []
        for r in rows:
            placeholders = extract_placeholders_from_text(r[13]) \
                + extract_placeholders_from_text(r[14]) \
                + extract_placeholders_from_text(r[15]) \
                + extract_placeholders_from_text(r[19])
            placeholders = sorted(set(placeholders))
            items.append(
                {
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
                    "request_url_params_template": r[13],
                    "request_body_template": r[14],
                    "request_headers_template": r[15],
                    "bearer_token": r[16],
                    "allow_caching": r[17],
                    "global_reuse": r[18],
                    "function_params_template": r[19],
                    "param_placeholders": placeholders,
                    "is_current_version": r[20]
                }
            )

        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@app.get("/ui/all_signals")
def list_all_signals(
    tenant_id: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
    active_only: bool = False,
):
    """Unpaginated signal list for dropdowns and bulk admin views."""
    return list_signals(
        checkpoint_id=checkpoint_id,
        tenant_id=tenant_id,
        page=1,
        size=10000,
        active_only=active_only,
    )["items"]


@app.get("/ui/signals/{signal_id}")
def get_signal(signal_id: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, tenant_id, name, description, type, method_of_call,
                   expression_body, cost, cache_expiration_seconds,
                   timeout_seconds, can_run_in_parallel, order_of_evaluation,
                   http_method, request_url_params_template,
                   request_body_template, request_headers_template,
                   bearer_token, allow_caching, global_reuse,
                   function_params_template
              FROM signals
             WHERE id = %s
            """,
            (signal_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Signal not found.")

        placeholders = extract_placeholders_from_text(row[13]) \
            + extract_placeholders_from_text(row[14]) \
            + extract_placeholders_from_text(row[15]) \
            + extract_placeholders_from_text(row[19])
        placeholders = sorted(set(placeholders))

        return {
            "id": str(row[0]),
            "tenant_id": row[1],
            "name": row[2],
            "description": row[3],
            "type": row[4],
            "method_of_call": row[5],
            "expression_body": row[6],
            "cost": row[7],
            "cache_expiration_seconds": row[8],
            "timeout_seconds": row[9],
            "can_run_in_parallel": row[10],
            "order_of_evaluation": row[11],
            "http_method": row[12],
            "request_url_params_template": row[13],
            "request_body_template": row[14],
            "request_headers_template": row[15],
            "bearer_token": row[16],
            "allow_caching": row[17],
            "global_reuse": row[18],
            "function_params_template": row[19],
            "param_placeholders": placeholders,
        }
    finally:
        if conn:
            conn.close()


@app.put("/ui/signals/{signal_id}")
def update_signal(signal_id: str, payload: SignalCreateUpdate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE signals
               SET tenant_id = %s,
                   name = %s,
                   description = %s,
                   type = %s,
                   method_of_call = %s,
                   expression_body = %s,
                   cost = %s,
                   cache_expiration_seconds = %s,
                   timeout_seconds = %s,
                   can_run_in_parallel = %s,
                   order_of_evaluation = %s,
                   http_method = %s,
                   request_url_params_template = %s,
                   request_body_template = %s,
                   request_headers_template = %s,
                   bearer_token = %s,
                   allow_caching = %s,
                   global_reuse = %s,
                   function_params_template = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (
                payload.tenant_id,
                payload.name,
                payload.description,
                payload.type,
                payload.method_of_call,
                payload.expression_body,
                payload.cost,
                payload.cache_expiration_seconds,
                payload.timeout_seconds,
                payload.can_run_in_parallel,
                payload.order_of_evaluation,
                payload.http_method,
                payload.request_url_params_template,
                payload.request_body_template,
                payload.request_headers_template,
                payload.bearer_token,
                payload.allow_caching,
                payload.global_reuse,
                payload.function_params_template,
                signal_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Signal not found.")
        conn.commit()
        return {"id": signal_id, **payload.dict()}
    finally:
        if conn:
            conn.close()


@app.delete("/ui/signals/{signal_id}")
def delete_signal(signal_id: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM signals WHERE id = %s", (signal_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Signal not found.")
        conn.commit()
        return {"deleted": True, "id": signal_id}
    finally:
        if conn:
            conn.close()


@app.post("/ui/variable_values")
def create_variable_value(payload: VariableValueCreateUpdate):
    """Create or update a row in signal_variable_values for a variable signal."""
    conn = None
    try:
        new_id = str(uuid.uuid4())
        conn = get_db_connection()
        cur = conn.cursor()
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
        return {"id": row_id, **payload.model_dump()}
    finally:
        if conn:
            conn.close()


@app.get("/ui/variable_values/{variable_value_id}")
def get_variable_value_item(variable_value_id: str):
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


@app.put("/ui/variable_values/{variable_value_id}")
def update_variable_value(variable_value_id: str, payload: VariableValueCreateUpdate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
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
        return {"id": variable_value_id, **payload.model_dump()}
    finally:
        if conn:
            conn.close()


@app.delete("/ui/variable_values/{variable_value_id}")
def delete_variable_value(variable_value_id: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM signal_variable_values WHERE id = %s", (variable_value_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Variable value not found.")
        conn.commit()
        return {"deleted": True, "id": variable_value_id}
    finally:
        if conn:
            conn.close()


@app.post("/ui/checkpoint_signals")
def create_checkpoint_signal(payload: CheckpointSignalCreateUpdate):
    conn = None
    try:
        new_id = str(uuid.uuid4())
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO checkpoint_signals
            (id, checkpoint_id, signal_id)
            VALUES (%s, %s, %s)
            """,
            (new_id, payload.checkpoint_id, payload.signal_id),
        )
        conn.commit()
        return {"id": new_id, **payload.dict()}
    finally:
        if conn:
            conn.close()


@app.delete("/ui/checkpoint_signals/{checkpoint_signal_id}")
def delete_checkpoint_signal(checkpoint_signal_id: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM checkpoint_signals WHERE id = %s", (checkpoint_signal_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Checkpoint-signal link not found.")
        conn.commit()
        return {"deleted": True, "id": checkpoint_signal_id}
    finally:
        if conn:
            conn.close()


@app.get("/ui/checkpoint_signals")
def list_checkpoint_signals(page: int = 1, size: int = 10):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        base_query = """
            SELECT cs.id, cs.checkpoint_id, cs.signal_id,
                   c.name as checkpoint_name, s.name as signal_name
              FROM checkpoint_signals cs
              JOIN checkpoints c ON cs.checkpoint_id = c.id
              JOIN signals s ON cs.signal_id = s.id
        """
        total, rows = paginate_query(cur, base_query, (), page, size)
        items = []
        for r in rows:
            items.append(
                {
                    "id": str(r[0]),
                    "checkpoint_id": str(r[1]),
                    "signal_id": str(r[2]),
                    "checkpoint_name": r[3],
                    "signal_name": r[4],
                }
            )
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@app.get("/ui/search_tenants")
def search_tenants(q: str, page: int = 1, size: int = 10):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        like = f"%{q}%"
        base_query = """
            SELECT id, name
              FROM tenants
             WHERE name ILIKE %s
                OR id::text ILIKE %s
        """
        params = (like, like)
        total, rows = paginate_query(cur, base_query, params, page, size)
        items = [{"id": str(r[0]), "name": r[1]} for r in rows]
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@app.get("/ui/search_checkpoints")
def search_checkpoints(q: str, page: int = 1, size: int = 10, active_only: bool = False):
    """
    Searches checkpoints by partial match in name, id::text, type, description,
    dsl_expression, or method_of_call.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        like = f"%{q}%"
        base_query = """
            SELECT c.id, c.tenant_id, c.name, c.description, c.type, c.dsl_expression,
                   CASE WHEN cv.checkpoint_id IS NOT NULL THEN true ELSE false END as is_current_version
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
        
        if active_only:
            base_query += " AND cv.checkpoint_id IS NOT NULL"

        total, rows = paginate_query(cur, base_query, params, page, size)
        items = []
        for r in rows:
            items.append({
                "id": str(r[0]),
                "tenant_id": str(r[1]),
                "name": r[2],
                "description": r[3],
                "type": r[4],
                "dsl_expression": r[5],
                "is_current_version": r[6]
            })
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@app.get("/ui/search_signals")
def search_signals(q: str, tenant_id: Optional[str] = None, page: int = 1, size: int = 10, active_only: bool = False):
    """
    Searches signals by partial match in name, id::text, type, description,
    or method_of_call. Returns placeholders too.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        like = f"%{q}%"
        base_query = """
            SELECT s.id, s.tenant_id, s.name, s.description, s.type, s.method_of_call,
                   s.expression_body, s.cost, s.cache_expiration_seconds, s.timeout_seconds,
                   s.can_run_in_parallel, s.order_of_evaluation, s.http_method,
                   s.request_url_params_template, s.request_body_template,
                   s.request_headers_template, s.bearer_token, s.allow_caching,
                   s.global_reuse, s.function_params_template,
                   CASE WHEN scv.signal_id IS NOT NULL THEN true ELSE false END as is_current_version
              FROM signals s
              LEFT JOIN signal_current_version scv ON scv.signal_id = s.id
             WHERE (s.name ILIKE %s
                OR s.id::text ILIKE %s
                OR s.type ILIKE %s
                OR s.description ILIKE %s
                OR s.method_of_call ILIKE %s)
        """
        params = [like, like, like, like, like]
        
        if tenant_id:
            base_query += " AND s.tenant_id = %s"
            params.append(tenant_id)
        
        if active_only:
            base_query += " AND scv.signal_id IS NOT NULL"

        total, rows = paginate_query(cur, base_query, params, page, size)
        items = []
        for r in rows:
            placeholders = extract_placeholders_from_text(r[13]) \
                + extract_placeholders_from_text(r[14]) \
                + extract_placeholders_from_text(r[15]) \
                + extract_placeholders_from_text(r[19])
            placeholders = sorted(set(placeholders))
            items.append(
                {
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
                    "request_url_params_template": r[13],
                    "request_body_template": r[14],
                    "request_headers_template": r[15],
                    "bearer_token": r[16],
                    "allow_caching": r[17],
                    "global_reuse": r[18],
                    "function_params_template": r[19],
                    "param_placeholders": placeholders,
                    "is_current_version": r[20]
                }
            )
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@app.get("/ui/search_decisions")
def search_decisions(
    q: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = 1,
    size: int = 10
):
    """
    Searches decisions by partial match in final_decision_value, correlation_id,
    applicant_id, checkpoint_id::text, or in signal_log.signal_value.
    Also optional date filters.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        base_query = """
            SELECT dl.id, dl.checkpoint_id, dl.tenant_id, dl.applicant_id,
                   dl.final_decision_value, dl.cost_incurred, dl.correlation_id,
                   dl.decision_timestamp
              FROM decision_log dl
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
                  OR sl.signal_value ILIKE %s
                )
                """
            )
            params.extend([like, like, like, like, like])

        if from_date:
            conditions.append("dl.decision_timestamp >= %s")
            params.append(from_date)
        if to_date:
            conditions.append("dl.decision_timestamp <= %s")
            params.append(to_date)

        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        base_query += " GROUP BY dl.id"

        total, rows = paginate_query(cur, base_query, params, page, size)
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
                }
            )
        return build_paginated_response(items, total, page, size)
    finally:
        if conn:
            conn.close()


@app.get("/ui/search_signal_logs")
def search_signal_logs(q: Optional[str] = None,
                       page: int = 1,
                       size: int = 10):
    """
    Searches signal_log by partial match in signal_id, applicant_id,
    decision_log_id, signal_value, cost_incurred, success, or id.
    Also includes param_values from signal_log_values.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Step 1: count how many overall signal_log rows match
        base_count_query = """
            SELECT COUNT(*)
              FROM signal_log
             WHERE 1=1
        """
        count_conditions = []
        count_params = []

        if q:
            like = f"%{q}%"
            count_conditions.append(
                """
                (
                  signal_id::text ILIKE %s
                  OR applicant_id ILIKE %s
                  OR decision_log_id::text ILIKE %s
                  OR signal_value ILIKE %s
                  OR CAST(cost_incurred AS text) ILIKE %s
                  OR CAST(success AS text) ILIKE %s
                  OR id::text ILIKE %s
                )
                """
            )
            count_params.extend([like, like, like, like, like, like, like])

        if count_conditions:
            base_count_query += " AND " + " AND ".join(count_conditions)

        cur.execute(base_count_query, count_params)
        total = cur.fetchone()[0]

        # Step 2: fetch actual rows (with left join to signal_log_values)
        base_data_query = """
            SELECT sl.id,
                   sl.decision_log_id,
                   sl.signal_id,
                   sl.applicant_id,
                   sl.signal_value,
                   sl.started_at,
                   sl.completed_at,
                   sl.cost_incurred,
                   sl.success,
                   slv.param_name,
                   slv.param_value
              FROM signal_log sl
         LEFT JOIN signal_log_values slv
                ON sl.id = slv.signal_log_id
             WHERE 1=1
        """
        data_conditions = []
        data_params = []

        if q:
            like = f"%{q}%"
            data_conditions.append(
                """
                (
                  sl.signal_id::text ILIKE %s
                  OR sl.applicant_id ILIKE %s
                  OR sl.decision_log_id::text ILIKE %s
                  OR sl.signal_value ILIKE %s
                  OR CAST(sl.cost_incurred AS text) ILIKE %s
                  OR CAST(sl.success AS text) ILIKE %s
                  OR sl.id::text ILIKE %s
                  OR slv.param_name ILIKE %s
                  OR slv.param_value ILIKE %s
                )
                """
            )
            data_params.extend([like, like, like, like, like, like, like, like, like])

        if data_conditions:
            base_data_query += " AND " + " AND ".join(data_conditions)

        base_data_query += " ORDER BY sl.started_at DESC"

        cur.execute(base_data_query, data_params)
        joined_rows = cur.fetchall()

        from collections import defaultdict
        log_map = defaultdict(lambda: {
            "id": None,
            "decision_log_id": None,
            "signal_id": None,
            "applicant_id": None,
            "signal_value": None,
            "started_at": None,
            "completed_at": None,
            "cost_incurred": None,
            "success": None,
            "param_values": []
        })

        for row in joined_rows:
            sl_id = str(row[0])
            if log_map[sl_id]["id"] is None:
                log_map[sl_id]["id"] = sl_id
                log_map[sl_id]["decision_log_id"] = str(row[1])
                log_map[sl_id]["signal_id"] = str(row[2])
                log_map[sl_id]["applicant_id"] = row[3]
                log_map[sl_id]["signal_value"] = row[4]
                log_map[sl_id]["started_at"] = row[5].isoformat() if row[5] else None
                log_map[sl_id]["completed_at"] = row[6].isoformat() if row[6] else None
                log_map[sl_id]["cost_incurred"] = row[7]
                log_map[sl_id]["success"] = row[8]

            param_name = row[9]
            param_val = row[10]
            if param_name is not None:
                log_map[sl_id]["param_values"].append({
                    "param_name": param_name,
                    "param_value": param_val
                })

        all_logs = list(log_map.values())

        # Apply pagination in memory
        start_index = (page - 1) * size
        end_index = start_index + size
        paginated_logs = all_logs[start_index:end_index]

        return {
            "items": paginated_logs,
            "total": total,
            "page": page,
            "size": size
        }

    finally:
        if conn:
            conn.close()


@app.post("/ui/checkpoints/{checkpoint_id}/make_current")
def make_checkpoint_current(checkpoint_id: str):
    """Make a checkpoint the current version for its tenant and name."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # First get the checkpoint details
        cur.execute("""
            SELECT tenant_id, name
            FROM checkpoints
            WHERE id = %s
        """, (checkpoint_id,))
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        
        tenant_id, checkpoint_name = result

        # Update or insert into checkpoint_current_version
        cur.execute("""
            INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, name) 
            DO UPDATE SET 
                checkpoint_id = EXCLUDED.checkpoint_id,
                updated_at = NOW()
        """, (tenant_id, checkpoint_name, checkpoint_id))
        
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.post("/ui/signals/{signal_id}/toggle_active")
def toggle_signal_active(signal_id: str):
    """Toggle a signal's active status by adding/removing it from signal_current_version."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get the tenant_id and name for this signal
        cur.execute("""
            SELECT tenant_id, name FROM signals 
            WHERE id = %s
        """, (signal_id,))
        signal = cur.fetchone()
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        tenant_id, signal_name = signal

        # Check if signal is currently active
        cur.execute("""
            SELECT signal_id FROM signal_current_version 
            WHERE tenant_id = %s AND name = %s
        """, (tenant_id, signal_name))
        is_active = cur.fetchone() is not None

        if is_active:
            # If active, remove from signal_current_version
            cur.execute("""
                DELETE FROM signal_current_version 
                WHERE tenant_id = %s AND name = %s
            """, (tenant_id, signal_name))
        else:
            # If not active, insert into signal_current_version
            cur.execute("""
                INSERT INTO signal_current_version (tenant_id, name, signal_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (tenant_id, name) DO UPDATE 
                SET signal_id = EXCLUDED.signal_id,
                    updated_at = NOW()
            """, (tenant_id, signal_name, signal_id))

        conn.commit()
        return {"success": True, "is_active": not is_active}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.post("/ui/signals/{signal_id}/make_current")
def make_signal_current(signal_id: str):
    """Set a signal as the current version for its tenant and name."""
    conn = get_db_connection()
    try:
        # Get the tenant_id and name for this signal
        cur = conn.cursor()
        cur.execute(
            "SELECT tenant_id, name FROM signals WHERE id = %s",
            (signal_id,)
        )
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        tenant_id, signal_name = result

        # Update or insert into signal_current_version
        cur.execute("""
            INSERT INTO signal_current_version (tenant_id, name, signal_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET signal_id = EXCLUDED.signal_id
        """, (tenant_id, signal_name, signal_id))
        
        conn.commit()
        return {"message": "Signal set as current version"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
