from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..auth import (
    AuthContext,
    assert_decision_tenant_access,
    get_auth_context,
    require_runtime,
    runtime_tenant_id,
)
from ..db import db_cursor
from ..models import DecisionRequest, DecisionResponse
from ..services.decision import execute_decision
from ..services.request_parsing import reject_runtime_tenant_query
from ..services.templates import build_template_explanation, decorate_dsl_expression
from ..services.security import redact_param_map_for_response, redact_template_for_response
from ..services.tenancy import (
    fetch_checkpoint_signal_details,
    fetch_current_checkpoint_row,
    fetch_current_signal_row,
)

router = APIRouter(tags=["runtime"])


@router.get(
    "/checkpoints/{checkpoint_name}",
    dependencies=[Depends(reject_runtime_tenant_query)],
)
def get_checkpoint_details(
    checkpoint_name: str,
    auth: AuthContext = Depends(require_runtime),
    resolved_tenant_id: str = Depends(runtime_tenant_id),
):
    with db_cursor() as (_, cur):
        row = fetch_current_checkpoint_row(cur, resolved_tenant_id, checkpoint_name)
        cp_data = row.to_dict()
        sig_rows = fetch_checkpoint_signal_details(cur, resolved_tenant_id, row.id)
        cp_data["signals"] = [s.to_runtime_dict() for s in sig_rows]
        return cp_data


@router.get(
    "/signals/{signal_name}",
    dependencies=[Depends(reject_runtime_tenant_query)],
)
def get_signal_details(
    signal_name: str,
    auth: AuthContext = Depends(require_runtime),
    resolved_tenant_id: str = Depends(runtime_tenant_id),
):
    with db_cursor() as (_, cur):
        return fetch_current_signal_row(cur, resolved_tenant_id, signal_name).to_runtime_dict()


@router.get("/decisions/{decision_id}")
def get_historical_decision(
    decision_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    with db_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT id, checkpoint_id, tenant_id, applicant_id,
                   decision_outcome, decision_reason, degraded,
                   final_decision_value, cost_incurred,
                   estimated_cost_units, reserved_cost_units, actual_cost_units,
                   budget_units, correlation_id, decision_timestamp
              FROM decision_log
             WHERE id = %s
            """,
            (decision_id,),
        )
        drow = cur.fetchone()
        if not drow:
            raise HTTPException(status_code=404, detail="Decision not found.")

        assert_decision_tenant_access(auth, str(drow[2]))

        decision_data = {
            "id": str(drow[0]),
            "checkpoint_id": str(drow[1]),
            "tenant_id": str(drow[2]),
            "applicant_id": drow[3],
            "decision_outcome": drow[4],
            "decision_reason": drow[5],
            "degraded": drow[6],
            "final_decision_value": drow[7] or drow[4],
            "cost_incurred": drow[8],
            "cost": {
                "estimated_units": drow[9] or 0,
                "reserved_units": drow[10] or 0,
                "actual_units": drow[11] or drow[8] or 0,
                "budget_units": drow[12],
            },
            "correlation_id": drow[13],
            "decision_timestamp": drow[14],
        }

        cur.execute(
            "SELECT name, dsl_expression FROM checkpoints WHERE id = %s",
            (drow[1],),
        )
        crow = cur.fetchone()
        checkpoint_dsl = crow[1] if crow else None
        decision_data["checkpoint_name"] = crow[0] if crow else None
        decision_data["checkpoint_dsl_expression"] = checkpoint_dsl

        cur.execute(
            """
            SELECT id, signal_id, applicant_id, signal_value,
                   started_at, completed_at, cost_incurred, success,
                   execution_status, criticality, estimated_cost_units,
                   reserved_cost_units, actual_cost_units, cache_hit,
                   skip_reason_code, error_message
              FROM signal_log
             WHERE decision_log_id = %s
            """,
            (decision_id,),
        )
        srows = cur.fetchall()

        signal_name_value_map = {}
        signal_details_list = []

        for s in srows:
            sl_id = str(s[0])
            sig_id = str(s[1])
            cur2 = conn.cursor()
            cur2.execute(
                """
                SELECT param_name, param_value
                  FROM signal_log_values
                 WHERE signal_log_id = %s
                """,
                (sl_id,),
            )
            param_map = redact_param_map_for_response(
                {pr[0]: pr[1] for pr in cur2.fetchall()}
            )
            cur2.close()

            cur3 = conn.cursor()
            cur3.execute(
                """
                SELECT name, method_of_call, request_url_params_template,
                       request_body_template, request_headers_template,
                       function_params_template, type
                  FROM signals
                 WHERE id = %s
                """,
                (sig_id,),
            )
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
                sig_name = "(unknown)"
                sig_method = ""
                sig_url_tmpl = ""
                sig_body_tmpl = ""
                sig_headers_tmpl = ""
                sig_func_tmpl = ""
                sig_type = "unknown"

            signal_name_value_map[sig_name] = s[3]
            signal_details_list.append(
                {
                    "signal_log_id": sl_id,
                    "signal_id": sig_id,
                    "signal_name": sig_name,
                    "signal_type": sig_type,
                    "signal_value": s[3],
                    "started_at": s[4],
                    "completed_at": s[5],
                    "cost_incurred": s[6],
                    "success": s[7],
                    "execution_status": s[8],
                    "criticality": s[9],
                    "estimated_cost_units": s[10],
                    "reserved_cost_units": s[11],
                    "actual_cost_units": s[12],
                    "cache_hit": s[13],
                    "skip_reason": s[14],
                    "error_message": s[15],
                    "param_values": param_map,
                    "original_templates": {
                        "request_url_params_template": redact_template_for_response(sig_url_tmpl),
                        "request_body_template": redact_template_for_response(sig_body_tmpl),
                        "request_headers_template": redact_template_for_response(sig_headers_tmpl),
                        "function_params_template": redact_template_for_response(sig_func_tmpl),
                    },
                    "rendered_explanations": {
                        "url_params": redact_template_for_response(
                            build_template_explanation(sig_url_tmpl, param_map)
                        ),
                        "body": redact_template_for_response(
                            build_template_explanation(sig_body_tmpl, param_map)
                        ),
                        "headers": redact_template_for_response(
                            build_template_explanation(sig_headers_tmpl, param_map)
                        ),
                        "function_params": redact_template_for_response(
                            build_template_explanation(sig_func_tmpl, param_map)
                        ),
                    },
                    "method_of_call": sig_method,
                }
            )

        decision_data["signals"] = signal_details_list
        decision_data["decorated_dsl_expression"] = (
            decorate_dsl_expression(checkpoint_dsl, signal_name_value_map) if checkpoint_dsl else None
        )
        return decision_data


@router.post("/decisions", response_model=DecisionResponse)
async def make_decision(
    payload: DecisionRequest,
    auth: AuthContext = Depends(require_runtime),
    tenant_id: str = Depends(runtime_tenant_id),
):
    return await execute_decision(tenant_id, payload, actor_id=auth.actor_id)
