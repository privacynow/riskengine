from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auth import TENANT_SUPPLIED_DETAIL


class TenantSuppliedError(Exception):
    """Raised when runtime clients attempt to supply tenant_id or tenant_name."""


class AdminTestDecisionRequest(BaseModel):
    tenant_id: str
    checkpoint_name: str
    applicant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class DecisionRequest(BaseModel):
    checkpoint_name: str
    applicant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_caller_tenant(cls, data: Any):
        if isinstance(data, dict) and ("tenant_id" in data or "tenant_name" in data):
            raise TenantSuppliedError(TENANT_SUPPLIED_DETAIL)
        return data


class DecisionResponse(BaseModel):
    decision_id: str
    final_decision_value: str
    cost_incurred: int
    signal_results: Dict[str, Any]


class TenantCreateUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    copy_from_tenant_id: Optional[str] = Field(None, alias="copyFromTenantId")


class CheckpointCreateUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: str
    name: str
    description: Optional[str] = None
    type: str
    dsl_expression: str
    method_of_call: Optional[str] = None
    max_cost: int = 0
    override_cost_flag: bool = False
    timeout_seconds: int = 30
    make_current_version: bool = Field(False, alias="makeCurrentVersion")


class SignalCreateUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

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
    make_current_version: bool = Field(False, alias="makeCurrentVersion")


class VariableValueCreateUpdate(BaseModel):
    signal_id: str
    name: str
    value: Optional[str] = None


class CheckpointSignalCreateUpdate(BaseModel):
    checkpoint_id: str
    signal_id: str
