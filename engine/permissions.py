"""Role-to-permission mapping for commercial deployments."""

from __future__ import annotations

_ALL_ADMIN_PERMISSIONS = frozenset(
    {
        "admin:read",
        "admin:write",
        "audit:read",
        "config:promote",
        "config:deactivate",
        "tenant:manage",
        "test:execute",
    }
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": _ALL_ADMIN_PERMISSIONS,
    "runtime": frozenset({"runtime:execute"}),
    "admin_readonly": frozenset({"admin:read"}),
    "audit_viewer": frozenset({"audit:read"}),
    "config_operator": frozenset(
        {"admin:read", "config:promote", "config:deactivate"}
    ),
    "test_runner": frozenset({"admin:read", "test:execute"}),
    "tenant_admin": frozenset({"admin:read", "tenant:manage"}),
}


def permissions_for_roles(roles: frozenset[str]) -> frozenset[str]:
    granted: set[str] = set()
    for role in roles:
        granted.update(ROLE_PERMISSIONS.get(role, frozenset()))
    return frozenset(granted)
