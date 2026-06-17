from fastapi import APIRouter

from ...models import CheckpointSignalCreateUpdate
from ...services.admin.checkpoint_signals import (
    create_checkpoint_signal,
    delete_checkpoint_signal,
    list_all_checkpoint_signals,
    list_checkpoint_signals,
)
from ...types import OptionalUuidStr, UuidStr
from ._deps import AdminRead, AdminWrite, ScopedTenantId

router = APIRouter()


@router.post("/ui/checkpoint_signals", dependencies=[AdminWrite])
def create_checkpoint_signal_route(payload: CheckpointSignalCreateUpdate):
    return create_checkpoint_signal(payload)


@router.delete("/ui/checkpoint_signals/{checkpoint_signal_id}", dependencies=[AdminWrite])
def delete_checkpoint_signal_route(checkpoint_signal_id: UuidStr):
    return delete_checkpoint_signal(checkpoint_signal_id)


@router.get("/ui/checkpoint_signals", dependencies=[AdminRead])
def list_checkpoint_signals_route(
    page: int = 1,
    size: int = 10,
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    checkpoint_id: OptionalUuidStr = None,
    signal_id: OptionalUuidStr = None,
):
    return list_checkpoint_signals(
        page=page,
        size=size,
        scoped_tenant_id=scoped_tenant_id,
        checkpoint_id=checkpoint_id,
        signal_id=signal_id,
    )


@router.get("/ui/all_checkpoint_signals", dependencies=[AdminRead])
def list_all_checkpoint_signals_route(
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    checkpoint_id: OptionalUuidStr = None,
    signal_id: OptionalUuidStr = None,
):
    return list_all_checkpoint_signals(
        scoped_tenant_id=scoped_tenant_id,
        checkpoint_id=checkpoint_id,
        signal_id=signal_id,
    )
