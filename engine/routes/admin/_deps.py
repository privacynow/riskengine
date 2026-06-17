"""Shared auth dependencies for admin routes."""

from fastapi import Depends

from ...auth import AuthContext, admin_tenant_query, get_auth_context, require_permission

AdminRead = Depends(require_permission("admin:read"))
AdminWrite = Depends(require_permission("admin:write"))
TenantManage = Depends(require_permission("tenant:manage"))
AuditRead = Depends(require_permission("audit:read"))
ConfigPromote = Depends(require_permission("config:promote"))
ConfigDeactivate = Depends(require_permission("config:deactivate"))
TestExecute = Depends(require_permission("test:execute"))
ScopedTenantId = Depends(admin_tenant_query)


def admin_read_auth(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if "admin:read" not in auth.permissions:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Missing required permission: admin:read")
    return auth


def audit_read_auth(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if "audit:read" not in auth.permissions:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Missing required permission: audit:read")
    return auth
