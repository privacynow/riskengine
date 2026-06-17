from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from psycopg2.extensions import cursor

from .secret_storage import decrypt_secret
from .templates import extract_placeholders_from_text


@dataclass(frozen=True)
class CheckpointRow:
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    type: str
    dsl_expression: str
    method_of_call: Optional[str]
    max_cost: Optional[int]
    override_cost_flag: bool
    budget_exceeded_policy: str
    vendor_failure_policy: str
    terminal_decline_signal_names: Tuple[str, ...]
    timeout_seconds: int

    @classmethod
    def from_db(cls, row) -> "CheckpointRow":
        terminal = row[11]
        return cls(
            id=str(row[0]),
            tenant_id=str(row[1]),
            name=row[2],
            description=row[3],
            type=row[4],
            dsl_expression=row[5],
            method_of_call=row[6],
            max_cost=row[7],
            override_cost_flag=row[8],
            budget_exceeded_policy=row[9],
            vendor_failure_policy=row[10],
            terminal_decline_signal_names=tuple(terminal or ()),
            timeout_seconds=row[12],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "dsl_expression": self.dsl_expression,
            "method_of_call": self.method_of_call,
            "max_cost": self.max_cost,
            "max_cost_units": self.max_cost,
            "override_cost_flag": self.override_cost_flag,
            "budget_exceeded_policy": self.budget_exceeded_policy,
            "vendor_failure_policy": self.vendor_failure_policy,
            "terminal_decline_signal_names": list(self.terminal_decline_signal_names),
            "timeout_seconds": self.timeout_seconds,
        }


_CHECKPOINT_SELECT = """
        SELECT c.id, c.tenant_id, c.name, c.description, c.type,
               c.dsl_expression, c.method_of_call, c.max_cost,
               c.override_cost_flag, c.budget_exceeded_policy,
               c.vendor_failure_policy, c.terminal_decline_signal_names,
               c.timeout_seconds
"""


@dataclass(frozen=True)
class ExecutableSignalRow:
    id: str
    name: str
    type: str
    method_of_call: Optional[str]
    expression_body: Optional[str]
    cost: int
    cache_expiration_seconds: int
    timeout_seconds: int
    can_run_in_parallel: bool
    order_of_evaluation: int
    http_method: Optional[str]
    request_url_params_template: Optional[str]
    request_body_template: Optional[str]
    request_headers_template: Optional[str]
    bearer_token: Optional[str]
    allow_caching: bool
    global_reuse: bool
    function_params_template: Optional[str]
    default_priority: int = 500
    effective_priority: int = 500
    criticality: str = "preferred"
    execution_role: str = "referenced_policy"
    effective_stage: int = 1
    vendor_audit_after_decline: bool = False
    billable_event: str = "success"
    cache_scope: str = "tenant_applicant_signal"
    is_expensive_vendor: bool = False

    @classmethod
    def from_db(cls, row) -> "ExecutableSignalRow":
        effective_stage = row[22] if len(row) > 22 else row[9]
        return cls(
            id=str(row[0]),
            name=row[1],
            type=row[2],
            method_of_call=row[3],
            expression_body=row[4],
            cost=row[5],
            cache_expiration_seconds=row[6],
            timeout_seconds=row[7],
            can_run_in_parallel=row[8],
            order_of_evaluation=row[9],
            http_method=row[10],
            request_url_params_template=row[11],
            request_body_template=row[12],
            request_headers_template=row[13],
            bearer_token=decrypt_secret(row[14]),
            allow_caching=row[15],
            global_reuse=row[16],
            function_params_template=row[17],
            default_priority=row[18] if len(row) > 18 else 500,
            effective_priority=row[19] if len(row) > 19 else (row[18] if len(row) > 18 else 500),
            criticality=row[20] if len(row) > 20 else "preferred",
            execution_role=row[21] if len(row) > 21 else "referenced_policy",
            effective_stage=effective_stage,
            vendor_audit_after_decline=bool(row[23]) if len(row) > 23 else False,
            billable_event=row[24] if len(row) > 24 else "success",
            cache_scope=row[25] if len(row) > 25 else "tenant_applicant_signal",
            is_expensive_vendor=bool(row[26]) if len(row) > 26 else False,
        )


@dataclass(frozen=True)
class SignalDetailRow(ExecutableSignalRow):
    tenant_id: str = ""
    description: Optional[str] = None

    @classmethod
    def from_db(cls, row) -> "SignalDetailRow":
        base = ExecutableSignalRow.from_db(row[:27])
        return cls(
            id=base.id,
            name=base.name,
            type=base.type,
            method_of_call=base.method_of_call,
            expression_body=base.expression_body,
            cost=base.cost,
            cache_expiration_seconds=base.cache_expiration_seconds,
            timeout_seconds=base.timeout_seconds,
            can_run_in_parallel=base.can_run_in_parallel,
            order_of_evaluation=base.order_of_evaluation,
            http_method=base.http_method,
            request_url_params_template=base.request_url_params_template,
            request_body_template=base.request_body_template,
            request_headers_template=base.request_headers_template,
            bearer_token=base.bearer_token,
            allow_caching=base.allow_caching,
            global_reuse=base.global_reuse,
            function_params_template=base.function_params_template,
            default_priority=base.default_priority,
            effective_priority=base.effective_priority,
            criticality=base.criticality,
            execution_role=base.execution_role,
            effective_stage=base.effective_stage,
            vendor_audit_after_decline=base.vendor_audit_after_decline,
            billable_event=base.billable_event,
            cache_scope=base.cache_scope,
            is_expensive_vendor=base.is_expensive_vendor,
            tenant_id=str(row[27]),
            description=row[28],
        )

    def to_runtime_dict(self) -> Dict[str, Any]:
        placeholders = extract_placeholders_from_text(self.request_url_params_template)
        placeholders += extract_placeholders_from_text(self.request_body_template)
        placeholders += extract_placeholders_from_text(self.request_headers_template)
        placeholders += extract_placeholders_from_text(self.function_params_template)
        placeholders = sorted(set(placeholders))
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "method_of_call": self.method_of_call,
            "expression_body": self.expression_body,
            "cost": self.cost,
            "cost_units": self.cost,
            "cache_expiration_seconds": self.cache_expiration_seconds,
            "timeout_seconds": self.timeout_seconds,
            "can_run_in_parallel": self.can_run_in_parallel,
            "order_of_evaluation": self.order_of_evaluation,
            "default_priority": self.default_priority,
            "billable_event": self.billable_event,
            "cache_scope": self.cache_scope,
            "is_expensive_vendor": self.is_expensive_vendor,
            "http_method": self.http_method,
            "allow_caching": self.allow_caching,
            "global_reuse": self.global_reuse,
            "param_placeholders": placeholders,
        }


CHECKPOINT_SIGNAL_EXECUTION_SQL = """
    WITH linked_associations AS (
        SELECT DISTINCT ON (linked_sig.name)
               linked_sig.name AS signal_name,
               cs.priority_override,
               cs.criticality,
               cs.execution_role,
               cs.stage_override,
               cs.vendor_audit_after_decline
          FROM checkpoint_signals cs
          JOIN signals linked_sig ON linked_sig.id = cs.signal_id
         WHERE cs.checkpoint_id = %s
         ORDER BY linked_sig.name, cs.created_at DESC
    )
    SELECT
           s_exec.id, s_exec.name, s_exec.type, s_exec.method_of_call, s_exec.expression_body,
           s_exec.cost, s_exec.cache_expiration_seconds, s_exec.timeout_seconds,
           s_exec.can_run_in_parallel, s_exec.order_of_evaluation,
           s_exec.http_method, s_exec.request_url_params_template,
           s_exec.request_body_template, s_exec.request_headers_template,
           s_exec.bearer_token, s_exec.allow_caching, s_exec.global_reuse,
           s_exec.function_params_template,
           s_exec.default_priority,
           COALESCE(la.priority_override, s_exec.default_priority) AS effective_priority,
           COALESCE(la.criticality, 'preferred') AS criticality,
           COALESCE(la.execution_role, 'referenced_policy') AS execution_role,
           COALESCE(la.stage_override, s_exec.order_of_evaluation) AS effective_stage,
           COALESCE(la.vendor_audit_after_decline, FALSE) AS vendor_audit_after_decline,
           s_exec.billable_event,
           s_exec.cache_scope,
           s_exec.is_expensive_vendor
      FROM linked_associations la
      JOIN signal_current_version scv
        ON scv.tenant_id = %s AND scv.name = la.signal_name
      JOIN signals s_exec
        ON s_exec.id = scv.signal_id
       AND s_exec.tenant_id = %s
     ORDER BY effective_stage, effective_priority, s_exec.name, s_exec.id
"""

CHECKPOINT_SIGNAL_DETAILS_SQL = """
    WITH linked_associations AS (
        SELECT DISTINCT ON (linked_sig.name)
               linked_sig.name AS signal_name,
               cs.priority_override,
               cs.criticality,
               cs.execution_role,
               cs.stage_override,
               cs.vendor_audit_after_decline
          FROM checkpoint_signals cs
          JOIN signals linked_sig ON linked_sig.id = cs.signal_id
         WHERE cs.checkpoint_id = %s
         ORDER BY linked_sig.name, cs.created_at DESC
    )
    SELECT
           s_exec.id, s_exec.name, s_exec.type, s_exec.method_of_call, s_exec.expression_body,
           s_exec.cost, s_exec.cache_expiration_seconds, s_exec.timeout_seconds,
           s_exec.can_run_in_parallel, s_exec.order_of_evaluation,
           s_exec.http_method, s_exec.request_url_params_template,
           s_exec.request_body_template, s_exec.request_headers_template,
           s_exec.bearer_token, s_exec.allow_caching, s_exec.global_reuse,
           s_exec.function_params_template,
           s_exec.default_priority,
           COALESCE(la.priority_override, s_exec.default_priority) AS effective_priority,
           COALESCE(la.criticality, 'preferred') AS criticality,
           COALESCE(la.execution_role, 'referenced_policy') AS execution_role,
           COALESCE(la.stage_override, s_exec.order_of_evaluation) AS effective_stage,
           COALESCE(la.vendor_audit_after_decline, FALSE) AS vendor_audit_after_decline,
           s_exec.billable_event,
           s_exec.cache_scope,
           s_exec.is_expensive_vendor,
           s_exec.tenant_id,
           s_exec.description
      FROM linked_associations la
      JOIN signal_current_version scv
        ON scv.tenant_id = %s AND scv.name = la.signal_name
      JOIN signals s_exec
        ON s_exec.id = scv.signal_id
       AND s_exec.tenant_id = %s
     ORDER BY effective_stage, effective_priority, s_exec.name, s_exec.id
"""


def fetch_checkpoint_row_by_id(cur: cursor, tenant_id: str, checkpoint_id: str) -> CheckpointRow:
    cur.execute(
        f"""
        {_CHECKPOINT_SELECT}
          FROM checkpoints c
         WHERE c.id = %s AND c.tenant_id = %s
        """,
        (checkpoint_id, tenant_id),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Checkpoint '{checkpoint_id}' not found for tenant.",
        )
    return CheckpointRow.from_db(row)


def fetch_current_checkpoint_row(cur: cursor, tenant_id: str, checkpoint_name: str) -> CheckpointRow:
    cur.execute(
        f"""
        {_CHECKPOINT_SELECT}
          FROM checkpoint_current_version cv
          JOIN checkpoints c ON c.id = cv.checkpoint_id
         WHERE cv.tenant_id = %s AND cv.name = %s
        """,
        (tenant_id, checkpoint_name),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No current checkpoint version for '{checkpoint_name}' in tenant.",
        )
    return CheckpointRow.from_db(row)


def fetch_executable_signal_rows(
    cur: cursor, tenant_id: str, checkpoint_id: str
) -> List[ExecutableSignalRow]:
    cur.execute(CHECKPOINT_SIGNAL_EXECUTION_SQL, (checkpoint_id, tenant_id, tenant_id))
    return [ExecutableSignalRow.from_db(row) for row in cur.fetchall()]


def fetch_checkpoint_signal_details(
    cur: cursor, tenant_id: str, checkpoint_id: str
) -> List[SignalDetailRow]:
    cur.execute(CHECKPOINT_SIGNAL_DETAILS_SQL, (checkpoint_id, tenant_id, tenant_id))
    return [SignalDetailRow.from_db(row) for row in cur.fetchall()]


def fetch_current_signal_row(cur: cursor, tenant_id: str, signal_name: str) -> SignalDetailRow:
    cur.execute(
        """
        SELECT s.id, s.name, s.type, s.method_of_call, s.expression_body,
               s.cost, s.cache_expiration_seconds, s.timeout_seconds,
               s.can_run_in_parallel, s.order_of_evaluation, s.http_method,
               s.request_url_params_template, s.request_body_template,
               s.request_headers_template, s.bearer_token, s.allow_caching,
               s.global_reuse, s.function_params_template,
               s.default_priority, s.default_priority,
               'preferred', 'referenced_policy', s.order_of_evaluation,
               FALSE, s.billable_event, s.cache_scope, s.is_expensive_vendor,
               s.tenant_id, s.description
          FROM signal_current_version scv
          JOIN signals s ON s.id = scv.signal_id
         WHERE scv.tenant_id = %s AND scv.name = %s
        """,
        (tenant_id, signal_name),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return SignalDetailRow.from_db(row)
