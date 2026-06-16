from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .auth import TENANT_SUPPLIED_DETAIL
from .types import parse_optional_uuid, parse_uuid


class TenantSuppliedError(Exception):
    """Raised when runtime clients attempt to supply tenant_id or tenant_name."""


class AdminTestDecisionRequest(BaseModel):
    tenant_id: str
    checkpoint_name: str
    checkpoint_id: Optional[str] = None
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


class CheckpointMetadataUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    description: Optional[str] = None


class CheckpointCreateRequest(BaseModel):
    """Config fields for a new checkpoint version (POST only)."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    tenant_id: str
    name: str
    description: Optional[str] = None
    type: str
    dsl_expression: str
    method_of_call: Optional[str] = None
    max_cost: int = 0
    override_cost_flag: bool = False
    timeout_seconds: int = 30
    signal_ids: List[str] = Field(default_factory=list, alias="signals")
    copy_from_checkpoint_id: Optional[str] = Field(None, alias="copyFromCheckpointId")

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _validate_tenant_id(cls, value: object) -> str:
        return parse_uuid(value, field="tenant_id")

    @field_validator("signal_ids", mode="before")
    @classmethod
    def _validate_signal_ids(cls, value: object) -> list[str]:
        if value is None:
            return []
        return [parse_uuid(item, field="signal_id") for item in value]

    @field_validator("copy_from_checkpoint_id", mode="before")
    @classmethod
    def _validate_copy_from_checkpoint_id(cls, value: object) -> Optional[str]:
        return parse_optional_uuid(value, field="copyFromCheckpointId")


class SignalMetadataUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    description: Optional[str] = None


class SignalCreateUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

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
    copy_from_signal_id: Optional[str] = Field(None, alias="copyFromSignalId")

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _validate_tenant_id(cls, value: object) -> str:
        return parse_uuid(value, field="tenant_id")

    @field_validator("copy_from_signal_id", mode="before")
    @classmethod
    def _validate_copy_from_signal_id(cls, value: object) -> Optional[str]:
        return parse_optional_uuid(value, field="copyFromSignalId")


class VariableValueCreateUpdate(BaseModel):
    signal_id: str
    name: str
    value: Optional[str] = None

    @field_validator("signal_id", mode="before")
    @classmethod
    def _validate_signal_id(cls, value: object) -> str:
        return parse_uuid(value, field="signal_id")


class DslPreflightRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    dsl_expression: str
    signal_names: List[str] = Field(default_factory=list)
    known_names: List[str] = Field(default_factory=list)
    binding_mode: Optional[Literal["strict", "warn_unknown", "syntax_only"]] = None
    expression_kind: Literal["checkpoint", "signal_expression"] = "checkpoint"


class PromotionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    promotion_reason: str = Field(..., alias="promotionReason", min_length=3, max_length=2000)


class DevTenantPurgeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    tenant_id: str = Field(..., alias="tenantId")
    purge_reason: str = Field(..., alias="purgeReason", min_length=10, max_length=2000)
    confirm_phrase: str = Field(..., alias="confirmPhrase")

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _validate_tenant_id(cls, value: object) -> str:
        return parse_uuid(value, field="tenant_id")


class CheckpointSignalCreateUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    checkpoint_id: str
    signal_id: str

    @field_validator("checkpoint_id", "signal_id", mode="before")
    @classmethod
    def _validate_ids(cls, value: object) -> str:
        return parse_uuid(value, field="id")

