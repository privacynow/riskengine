from fastapi import APIRouter, Depends

from ...auth import AuthContext, require_permission
from ...models import TenantCreateUpdate
from ...services.admin.tenants import (
    create_tenant,
    delete_tenant,
    get_tenant,
    list_all_tenants,
    list_tenants,
    update_tenant,
)
from ...types import UuidStr
from ._deps import AdminRead, admin_read_auth

router = APIRouter()


@router.post("/ui/tenants")
def create_tenant_route(
    payload: TenantCreateUpdate,
    auth: AuthContext = Depends(require_permission("tenant:manage")),
):
    return create_tenant(payload, auth=auth)


@router.get("/ui/tenants", dependencies=[AdminRead])
def list_tenants_route(
    page: int = 1,
    size: int = 10,
    auth: AuthContext = Depends(admin_read_auth),
):
    return list_tenants(auth=auth, page=page, size=size)


@router.get("/ui/all_tenants", dependencies=[AdminRead])
def list_all_tenants_route(auth: AuthContext = Depends(admin_read_auth)):
    return list_all_tenants(auth=auth)


@router.get("/ui/tenants/{tenant_id}", dependencies=[AdminRead])
def get_tenant_route(tenant_id: UuidStr, auth: AuthContext = Depends(admin_read_auth)):
    return get_tenant(tenant_id, auth=auth)


@router.put("/ui/tenants/{tenant_id}")
def update_tenant_route(
    tenant_id: UuidStr,
    payload: TenantCreateUpdate,
    auth: AuthContext = Depends(require_permission("tenant:manage")),
):
    return update_tenant(tenant_id, payload, auth=auth)


@router.delete("/ui/tenants/{tenant_id}")
def delete_tenant_route(
    tenant_id: UuidStr,
    auth: AuthContext = Depends(require_permission("tenant:manage")),
):
    return delete_tenant(tenant_id, auth=auth)
