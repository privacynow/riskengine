from fastapi import APIRouter, Depends

from ...auth import AuthContext
from ...models import SignalCreateUpdate, SignalMetadataUpdate
from ...services.admin.signals import (
    create_signal,
    delete_signal,
    get_signal,
    list_all_signals,
    list_signals,
    update_signal,
)
from ...services.admin.versions import list_signal_versions
from ...types import OptionalUuidStr, UuidStr
from ._deps import AdminRead, AdminWrite, ScopedTenantId, admin_read_auth

router = APIRouter()


@router.post("/ui/signals", dependencies=[AdminWrite])
def create_signal_route(payload: SignalCreateUpdate):
    return create_signal(payload)


@router.get("/ui/signals", dependencies=[AdminRead])
def list_signals_route(
    checkpoint_id: OptionalUuidStr = None,
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
):
    return list_signals(
        checkpoint_id=checkpoint_id,
        scoped_tenant_id=scoped_tenant_id,
        page=page,
        size=size,
        active_only=active_only,
    )


@router.get("/ui/all_signals", dependencies=[AdminRead])
def list_all_signals_route(
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    checkpoint_id: OptionalUuidStr = None,
    active_only: bool = False,
):
    return list_all_signals(
        scoped_tenant_id=scoped_tenant_id,
        checkpoint_id=checkpoint_id,
        active_only=active_only,
    )


@router.get("/ui/signals/{signal_id}/versions", dependencies=[AdminRead])
def list_signal_versions_route(
    signal_id: UuidStr,
    auth: AuthContext = Depends(admin_read_auth),
):
    return {"items": list_signal_versions(signal_id, auth=auth)}


@router.get("/ui/signals/{signal_id}", dependencies=[AdminRead])
def get_signal_route(
    signal_id: UuidStr,
    auth: AuthContext = Depends(admin_read_auth),
):
    return get_signal(signal_id, auth=auth)


@router.put("/ui/signals/{signal_id}", dependencies=[AdminWrite])
def update_signal_route(signal_id: UuidStr, payload: SignalMetadataUpdate):
    return update_signal(signal_id, payload)


@router.delete("/ui/signals/{signal_id}", dependencies=[AdminWrite])
def delete_signal_route(signal_id: UuidStr):
    return delete_signal(signal_id)
