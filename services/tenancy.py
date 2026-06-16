from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from psycopg2.extensions import cursor

from services.templates import extract_placeholders_from_text


@dataclass(frozen=True)
class CheckpointRow:
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    type: str
    dsl_expression: str
    method_of_call: Optional[str]
    max_cost: int
    override_cost_flag: bool
    timeout_seconds: int

    @classmethod
    def from_db(cls, row) -> "CheckpointRow":
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
            timeout_seconds=row[9],
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
            "override_cost_flag": self.override_cost_flag,
            "timeout_seconds": self.timeout_seconds,
        }


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

    @classmethod
    def from_db(cls, row) -> "ExecutableSignalRow":
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
            bearer_token=row[14],
            allow_caching=row[15],
            global_reuse=row[16],
            function_params_template=row[17],
        )


@dataclass(frozen=True)
class SignalDetailRow(ExecutableSignalRow):
    tenant_id: str
    description: Optional[str]

    @classmethod
    def from_db(cls, row) -> "SignalDetailRow":
        return cls(
            id=str(row[0]),
            tenant_id=str(row[1]),
            name=row[2],
            description=row[3],
            type=row[4],
            method_of_call=row[5],
            expression_body=row[6],
            cost=row[7],
            cache_expiration_seconds=row[8],
            timeout_seconds=row[9],
            can_run_in_parallel=row[10],
            order_of_evaluation=row[11],
            http_method=row[12],
            request_url_params_template=row[13],
            request_body_template=row[14],
            request_headers_template=row[15],
            bearer_token=row[16],
            allow_caching=row[17],
            global_reuse=row[18],
            function_params_template=row[19],
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
            "cache_expiration_seconds": self.cache_expiration_seconds,
            "timeout_seconds": self.timeout_seconds,
            "can_run_in_parallel": self.can_run_in_parallel,
            "order_of_evaluation": self.order_of_evaluation,
            "http_method": self.http_method,
            "allow_caching": self.allow_caching,
            "global_reuse": self.global_reuse,
            "param_placeholders": placeholders,
        }


CHECKPOINT_SIGNAL_EXECUTION_SQL = """
    SELECT s_exec.id, s_exec.name, s_exec.type, s_exec.method_of_call, s_exec.expression_body,
           s_exec.cost, s_exec.cache_expiration_seconds, s_exec.timeout_seconds,
           s_exec.can_run_in_parallel, s_exec.order_of_evaluation,
           s_exec.http_method, s_exec.request_url_params_template,
           s_exec.request_body_template, s_exec.request_headers_template,
           s_exec.bearer_token, s_exec.allow_caching, s_exec.global_reuse,
           s_exec.function_params_template
      FROM checkpoint_signals cs
      JOIN signals s ON s.id = cs.signal_id
      JOIN signal_current_version scv
        ON scv.tenant_id = %s AND scv.name = s.name
      JOIN signals s_exec
        ON s_exec.id = scv.signal_id
       AND s_exec.tenant_id = %s
     WHERE cs.checkpoint_id = %s
     ORDER BY s_exec.order_of_evaluation, s_exec.name
"""

CHECKPOINT_SIGNAL_DETAILS_SQL = """
    SELECT s_exec.id, s_exec.tenant_id, s_exec.name, s_exec.description, s_exec.type,
           s_exec.method_of_call, s_exec.expression_body, s_exec.cost,
           s_exec.cache_expiration_seconds, s_exec.timeout_seconds,
           s_exec.can_run_in_parallel, s_exec.order_of_evaluation,
           s_exec.http_method, s_exec.request_url_params_template,
           s_exec.request_body_template, s_exec.request_headers_template,
           s_exec.bearer_token, s_exec.allow_caching, s_exec.global_reuse,
           s_exec.function_params_template
      FROM checkpoint_signals cs
      JOIN signals s ON s.id = cs.signal_id
      JOIN signal_current_version scv
        ON scv.tenant_id = %s AND scv.name = s.name
      JOIN signals s_exec
        ON s_exec.id = scv.signal_id
       AND s_exec.tenant_id = %s
     WHERE cs.checkpoint_id = %s
     ORDER BY s_exec.order_of_evaluation, s_exec.name
"""


def fetch_current_checkpoint_row(cur: cursor, tenant_id: str, checkpoint_name: str) -> CheckpointRow:
    cur.execute(
        """
        SELECT c.id, c.tenant_id, c.name, c.description, c.type,
               c.dsl_expression, c.method_of_call, c.max_cost,
               c.override_cost_flag, c.timeout_seconds
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
    cur.execute(CHECKPOINT_SIGNAL_EXECUTION_SQL, (tenant_id, tenant_id, checkpoint_id))
    return [ExecutableSignalRow.from_db(row) for row in cur.fetchall()]


def fetch_checkpoint_signal_details(
    cur: cursor, tenant_id: str, checkpoint_id: str
) -> List[SignalDetailRow]:
    cur.execute(CHECKPOINT_SIGNAL_DETAILS_SQL, (tenant_id, tenant_id, checkpoint_id))
    return [SignalDetailRow.from_db(row) for row in cur.fetchall()]


def fetch_current_signal_row(cur: cursor, tenant_id: str, signal_name: str) -> SignalDetailRow:
    cur.execute(
        """
        SELECT s.id, s.tenant_id, s.name, s.description, s.type, s.method_of_call,
               s.expression_body, s.cost, s.cache_expiration_seconds, s.timeout_seconds,
               s.can_run_in_parallel, s.order_of_evaluation, s.http_method,
               s.request_url_params_template, s.request_body_template,
               s.request_headers_template, s.bearer_token, s.allow_caching,
               s.global_reuse, s.function_params_template
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
