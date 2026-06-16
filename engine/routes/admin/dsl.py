from fastapi import APIRouter

from ...models import DslPreflightRequest
from ...services.dsl_preflight import preflight_dsl
from ._deps import AdminRead

router = APIRouter(dependencies=[AdminRead])

@router.post("/ui/dsl_preflight")
def dsl_preflight(payload: DslPreflightRequest):
    """Validate DSL syntax using the same policy as runtime evaluation."""
    known_names = list(payload.signal_names) + list(payload.known_names)
    return preflight_dsl(
        payload.dsl_expression,
        known_names,
        binding_mode=payload.binding_mode,
        expression_kind=payload.expression_kind,
    )
