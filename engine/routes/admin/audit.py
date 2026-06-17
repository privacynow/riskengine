from typing import Optional

from fastapi import APIRouter, Depends

from ...auth import AuthContext, audit_tenant_query
from ...services.admin.audit import get_promotion_audit, search_promotion_audit
from ...types import OptionalUuidStr, UuidStr
from ._deps import AuditRead, audit_read_auth

router = APIRouter(dependencies=[AuditRead])


@router.get("/ui/promotion_audit")
def search_promotion_audit_route(
    scoped_tenant_id: OptionalUuidStr = Depends(audit_tenant_query),
    q: Optional[str] = None,
    action: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    auth: AuthContext = Depends(audit_read_auth),
):
    return search_promotion_audit(
        tenant_id=scoped_tenant_id,
        q=q,
        action=action,
        page=page,
        size=size,
        auth=auth,
    )


@router.get("/ui/promotion_audit/{promotion_id}")
def get_promotion_audit_route(
    promotion_id: UuidStr,
    scoped_tenant_id: OptionalUuidStr = Depends(audit_tenant_query),
    auth: AuthContext = Depends(audit_read_auth),
):
    return get_promotion_audit(
        promotion_id,
        tenant_id=scoped_tenant_id,
        auth=auth,
    )
