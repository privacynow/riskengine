from typing import Optional

from fastapi import APIRouter

from ...services.admin.search import (
    search_checkpoints,
    search_decisions,
    search_signal_logs,
    search_signals,
    search_tenants,
)
from ...types import OptionalUuidStr
from ._deps import AdminRead, ScopedTenantId

router = APIRouter(dependencies=[AdminRead])


@router.get("/ui/search_tenants")
def search_tenants_route(q: str, page: int = 1, size: int = 10):
    return search_tenants(q=q, page=page, size=size)


@router.get("/ui/search_checkpoints")
def search_checkpoints_route(
    q: str,
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
):
    return search_checkpoints(
        q=q,
        scoped_tenant_id=scoped_tenant_id,
        page=page,
        size=size,
        active_only=active_only,
    )


@router.get("/ui/search_signals")
def search_signals_route(
    q: str,
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
):
    return search_signals(
        q=q,
        scoped_tenant_id=scoped_tenant_id,
        page=page,
        size=size,
        active_only=active_only,
    )


@router.get("/ui/search_decisions")
def search_decisions_route(
    q: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    page: int = 1,
    size: int = 10,
):
    return search_decisions(
        q=q,
        from_date=from_date,
        to_date=to_date,
        scoped_tenant_id=scoped_tenant_id,
        page=page,
        size=size,
    )


@router.get("/ui/search_signal_logs")
def search_signal_logs_route(
    q: Optional[str] = None,
    scoped_tenant_id: OptionalUuidStr = ScopedTenantId,
    failures_only: bool = False,
    param_name: Optional[str] = None,
    param_value: Optional[str] = None,
    page: int = 1,
    size: int = 10,
):
    return search_signal_logs(
        q=q,
        scoped_tenant_id=scoped_tenant_id,
        failures_only=failures_only,
        param_name=param_name,
        param_value=param_value,
        page=page,
        size=size,
    )
