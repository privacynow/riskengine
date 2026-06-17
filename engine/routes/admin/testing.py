from fastapi import APIRouter, Depends, HTTPException

from ...auth import AuthContext, require_permission, resolve_admin_tenant_id
from ...models import AdminTestDecisionRequest, DecisionRequest, DecisionResponse
from ...services.decision import execute_decision
from ...services.tenant_budget import normalize_override_reason

router = APIRouter()

@router.post("/ui/test_decisions", response_model=DecisionResponse)
async def admin_test_decision(
    payload: AdminTestDecisionRequest,
    auth: AuthContext = Depends(require_permission("test:execute")),
):
    """Run a checkpoint decision for a tenant without exposing runtime tokens to the client."""
    resolve_admin_tenant_id(auth, payload.tenant_id, required=True)
    if payload.budget_override:
        try:
            normalize_override_reason(payload.override_reason)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    decision_request = DecisionRequest(
        checkpoint_name=payload.checkpoint_name,
        applicant_id=payload.applicant_id,
        correlation_id=payload.correlation_id,
        parameters=payload.parameters,
    )
    return await execute_decision(
        payload.tenant_id,
        decision_request,
        actor_id=auth.actor_id,
        checkpoint_id=payload.checkpoint_id,
        include_manual_test=payload.include_manual_test,
        budget_override=payload.budget_override,
        override_reason=payload.override_reason,
    )
