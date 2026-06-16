"""Shared auth dependencies for admin routes."""

from fastapi import Depends

from ...auth import require_permission

AdminRead = Depends(require_permission("admin:read"))
AdminWrite = Depends(require_permission("admin:write"))
TenantManage = Depends(require_permission("tenant:manage"))
AuditRead = Depends(require_permission("audit:read"))
ConfigPromote = Depends(require_permission("config:promote"))
ConfigDeactivate = Depends(require_permission("config:deactivate"))
TestExecute = Depends(require_permission("test:execute"))
