"""Bearer token auth configuration and dependencies."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import db_cursor
from .permissions import permissions_for_roles

AUTH_CONFIG_HELP = (
    "Set DECISION_ENGINE_AUTH_TOKENS (JSON object) or DECISION_ENGINE_AUTH_TOKENS_FILE "
    "(path to JSON), and/or DECISION_ENGINE_JWT_HS256_SECRET for JWT-only auth "
    "(optional DECISION_ENGINE_JWT_ISSUER / DECISION_ENGINE_JWT_AUDIENCE). "
    "Local bootstrap: bash scripts/create_demo_env.sh"
)

_bearer = HTTPBearer(auto_error=False)
_token_map: Optional[Dict[str, Dict[str, Any]]] = None


def _parse_token_map(raw: str) -> Dict[str, Dict[str, Any]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Auth token configuration must be valid JSON.") from exc
    if not isinstance(parsed, dict) or not parsed:
        raise RuntimeError("Auth token configuration must be a non-empty JSON object.")
    return parsed


def _validate_token_map(token_map: Dict[str, Dict[str, Any]]) -> None:
    for index, (token, entry) in enumerate(token_map.items()):
        if not token or not isinstance(entry, dict):
            raise RuntimeError(f"Invalid auth entry at index {index}.")
        roles = entry.get("roles")
        if not isinstance(roles, list) or not roles:
            raise RuntimeError(f"Auth entry at index {index} must define a non-empty roles list.")
        if "runtime" in roles and not entry.get("tenant_id"):
            raise RuntimeError(f"Runtime auth entry at index {index} must include tenant_id.")


def _jwt_configured() -> bool:
    secret, _, _ = _jwt_settings()
    return bool(secret)


def _read_auth_config_raw() -> str | None:
    raw = os.environ.get("DECISION_ENGINE_AUTH_TOKENS")
    if raw is not None and raw.strip():
        return raw
    file_path = os.environ.get("DECISION_ENGINE_AUTH_TOKENS_FILE")
    if file_path:
        path = Path(file_path)
        if not path.is_file():
            raise RuntimeError(f"DECISION_ENGINE_AUTH_TOKENS_FILE not found: {file_path}")
        return path.read_text(encoding="utf-8")
    if _jwt_configured():
        return None
    raise RuntimeError(f"Missing auth configuration. {AUTH_CONFIG_HELP}")


def load_token_map() -> Dict[str, Dict[str, Any]]:
    raw = _read_auth_config_raw()
    if raw is None:
        return {}
    token_map = _parse_token_map(raw)
    _validate_token_map(token_map)
    return token_map


def initialize_auth() -> None:
    """Load and validate auth config at application startup."""
    global _token_map
    _token_map = load_token_map()


def get_token_map() -> Dict[str, Dict[str, Any]]:
    if _token_map is None:
        raise RuntimeError("Auth is not initialized. Call initialize_auth() at startup.")
    return _token_map


@dataclass(frozen=True)
class AuthContext:
    actor_id: str
    tenant_id: Optional[str]
    roles: frozenset[str]
    auth_method: str = "static_token"

    @property
    def permissions(self) -> frozenset[str]:
        return permissions_for_roles(self.roles)

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    @property
    def is_runtime(self) -> bool:
        return "runtime" in self.roles


def _jwt_settings() -> tuple[str | None, str | None, str | None]:
    secret = os.environ.get("DECISION_ENGINE_JWT_HS256_SECRET", "").strip() or None
    issuer = os.environ.get("DECISION_ENGINE_JWT_ISSUER", "").strip() or None
    audience = os.environ.get("DECISION_ENGINE_JWT_AUDIENCE", "").strip() or None
    return secret, issuer, audience


def _auth_context_from_jwt(token: str) -> AuthContext | None:
    secret, issuer, audience = _jwt_settings()
    if not secret:
        return None
    options = {"require": ["exp", "sub"]}
    decode_kwargs: dict[str, Any] = {"algorithms": ["HS256"], "options": options}
    if issuer:
        decode_kwargs["issuer"] = issuer
    if audience:
        decode_kwargs["audience"] = audience
    try:
        claims = jwt.decode(token, secret, **decode_kwargs)
    except jwt.PyJWTError:
        return None
    roles_raw = claims.get("roles") or claims.get("role") or []
    if isinstance(roles_raw, str):
        roles = frozenset({roles_raw})
    elif isinstance(roles_raw, list):
        roles = frozenset(str(r) for r in roles_raw)
    else:
        roles = frozenset()
    tenant_id = claims.get("tenant_id")
    return AuthContext(
        actor_id=str(claims.get("sub") or claims.get("actor_id") or "unknown"),
        tenant_id=str(tenant_id) if tenant_id else None,
        roles=roles,
        auth_method="jwt",
    )


def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required.")
    token = credentials.credentials
    entry = get_token_map().get(token)
    if entry:
        roles = frozenset(entry.get("roles") or [])
        return AuthContext(
            actor_id=str(entry.get("actor_id") or "unknown"),
            tenant_id=entry.get("tenant_id"),
            roles=roles,
            auth_method="static_token",
        )
    jwt_ctx = _auth_context_from_jwt(token)
    if jwt_ctx:
        return jwt_ctx
    raise HTTPException(status_code=401, detail="Invalid or unknown token.")


def require_permission(permission: str):
    def _dependency(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if permission not in auth.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permission: {permission}",
            )
        return auth

    return _dependency


def require_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not auth.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required.")
    return auth


def require_runtime(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not auth.is_runtime:
        raise HTTPException(status_code=403, detail="Runtime role required.")
    if not auth.tenant_id:
        raise HTTPException(status_code=403, detail="Runtime token must be bound to a tenant.")
    return auth


TENANT_SUPPLIED_DETAIL = (
    "Tenant cannot be supplied by runtime clients; it is derived from authentication."
)


def reject_supplied_tenant(
    *,
    has_tenant_id: bool = False,
    has_tenant_name: bool = False,
) -> None:
    if has_tenant_id or has_tenant_name:
        raise HTTPException(status_code=403, detail=TENANT_SUPPLIED_DETAIL)


def runtime_tenant_id(auth: AuthContext = Depends(require_runtime)) -> str:
    assert auth.tenant_id is not None
    return auth.tenant_id


def resolve_admin_tenant_id(
    auth: AuthContext,
    tenant_id: Optional[str],
    *,
    required: bool = True,
) -> Optional[str]:
    if tenant_id:
        with db_cursor() as (_, cur):
            cur.execute("SELECT id FROM tenants WHERE id = %s", (tenant_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Tenant not found.")
        return tenant_id
    if required and not auth.is_admin:
        raise HTTPException(status_code=422, detail="tenant_id is required.")
    return None


def admin_tenant_query(
    tenant_id: Optional[str] = Query(None),
    auth: AuthContext = Depends(require_permission("admin:read")),
) -> Optional[str]:
    if tenant_id:
        return resolve_admin_tenant_id(auth, tenant_id, required=False)
    return None


def assert_decision_tenant_access(auth: AuthContext, decision_tenant_id: str) -> None:
    if auth.is_admin:
        return
    if auth.tenant_id != decision_tenant_id:
        raise HTTPException(status_code=404, detail="Decision not found.")
