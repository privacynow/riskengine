from fastapi import APIRouter, Depends

from ...auth import AuthContext
from ...models import CheckpointCreateRequest, CheckpointMetadataUpdate
from ...services.admin.checkpoints import (
    create_checkpoint,
    delete_checkpoint,
    get_checkpoint,
    list_all_checkpoints,
    list_checkpoints,
    update_checkpoint,
)
from ...services.admin.versions import list_checkpoint_versions
from ...types import OptionalUuidStr, UuidStr
from ._deps import AdminRead, AdminWrite, ScopedTenantId, admin_read_auth

router = APIRouter()


@router.post("/ui/checkpoints", dependencies=[AdminWrite])
def create_checkpoint_route(payload: CheckpointCreateRequest):
    return create_checkpoint(payload)


@router.get("/ui/checkpoints", dependencies=[AdminRead])
def list_checkpoints_route(
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
):
    return list_checkpoints(
        scoped_tenant_id=scoped_tenant_id,
        page=page,
        size=size,
        active_only=active_only,
    )


@router.get("/ui/all_checkpoints", dependencies=[AdminRead])
def list_all_checkpoints_route(
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    active_only: bool = False,
):
    return list_all_checkpoints(
        scoped_tenant_id=scoped_tenant_id,
        active_only=active_only,
    )


@router.get("/ui/checkpoints/{checkpoint_id}/versions", dependencies=[AdminRead])
def list_checkpoint_versions_route(
    checkpoint_id: UuidStr,
    auth: AuthContext = Depends(admin_read_auth),
):
    return {"items": list_checkpoint_versions(checkpoint_id, auth=auth)}


@router.get("/ui/checkpoints/{checkpoint_id}", dependencies=[AdminRead])
def get_checkpoint_route(
    checkpoint_id: UuidStr,
    auth: AuthContext = Depends(admin_read_auth),
):
    return get_checkpoint(checkpoint_id, auth=auth)


@router.put("/ui/checkpoints/{checkpoint_id}", dependencies=[AdminWrite])
def update_checkpoint_route(checkpoint_id: UuidStr, payload: CheckpointMetadataUpdate):
    return update_checkpoint(checkpoint_id, payload)


@router.delete("/ui/checkpoints/{checkpoint_id}", dependencies=[AdminWrite])
def delete_checkpoint_route(checkpoint_id: UuidStr):
    return delete_checkpoint(checkpoint_id)
