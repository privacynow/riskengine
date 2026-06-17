from fastapi import APIRouter, Depends

from ...auth import AuthContext
from ...models import DslPreflightRequest
from ...services.admin.common import assert_checkpoint_resource_access
from ...services.dsl_preflight import list_checkpoint_linked_signal_names, preflight_dsl
from ._deps import admin_read_auth

router = APIRouter()


@router.post("/ui/dsl_preflight")
def dsl_preflight(
    payload: DslPreflightRequest,
    auth: AuthContext = Depends(admin_read_auth),
):
    """Validate DSL syntax using the same policy as runtime evaluation."""
    signal_names = list(payload.signal_names)
    if payload.checkpoint_id:
        assert_checkpoint_resource_access(auth, payload.checkpoint_id)
        linked_names = list_checkpoint_linked_signal_names(payload.checkpoint_id)
        signal_names = list(dict.fromkeys(linked_names + signal_names))

    known_names = signal_names + list(payload.known_names)
    return preflight_dsl(
        payload.dsl_expression,
        known_names,
        binding_mode=payload.binding_mode,
        expression_kind=payload.expression_kind,
    )
