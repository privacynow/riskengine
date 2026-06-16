"""Role-to-permission mapping for commercial deployments."""

from __future__ import annotations

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset(
        {
            "admin:read",
            "admin:write",
            "audit:read",
            "config:promote",
            "config:deactivate",
            "tenant:manage",
            "test:execute",
        }
    ),
    "runtime": frozenset({"runtime:execute"}),
}


def permissions_for_roles(roles: frozenset[str]) -> frozenset[str]:
    granted: set[str] = set()
    for role in roles:
        granted.update(ROLE_PERMISSIONS.get(role, frozenset()))
    return frozenset(granted)
