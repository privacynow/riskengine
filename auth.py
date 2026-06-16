"""Bearer token auth configuration and dependencies."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import db_cursor

AUTH_CONFIG_HELP = (
    "Set DECISION_ENGINE_AUTH_TOKENS (JSON object) or DECISION_ENGINE_AUTH_TOKENS_FILE "
    "(path to JSON). For local demo: bash scripts/create_demo_env.sh"
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


def _read_auth_config_raw() -> str:
    raw = os.environ.get("DECISION_ENGINE_AUTH_TOKENS")
    if raw:
        return raw
    file_path = os.environ.get("DECISION_ENGINE_AUTH_TOKENS_FILE")
    if file_path:
        path = Path(file_path)
        if not path.is_file():
            raise RuntimeError(f"DECISION_ENGINE_AUTH_TOKENS_FILE not found: {file_path}")
        return path.read_text(encoding="utf-8")
    raise RuntimeError(f"Missing auth configuration. {AUTH_CONFIG_HELP}")


def load_token_map() -> Dict[str, Dict[str, Any]]:
    token_map = _parse_token_map(_read_auth_config_raw())
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

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    @property
    def is_runtime(self) -> bool:
        return "runtime" in self.roles


def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required.")
    token = credentials.credentials
    entry = get_token_map().get(token)
    if not entry:
        raise HTTPException(status_code=401, detail="Invalid or unknown token.")
    roles = frozenset(entry.get("roles") or [])
    return AuthContext(
        actor_id=str(entry.get("actor_id") or "unknown"),
        tenant_id=entry.get("tenant_id"),
        roles=roles,
    )


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
    auth: AuthContext = Depends(require_admin),
) -> Optional[str]:
    if tenant_id:
        return resolve_admin_tenant_id(auth, tenant_id, required=False)
    return None


def assert_decision_tenant_access(auth: AuthContext, decision_tenant_id: str) -> None:
    if auth.is_admin:
        return
    if auth.tenant_id != decision_tenant_id:
        raise HTTPException(status_code=404, detail="Decision not found.")
