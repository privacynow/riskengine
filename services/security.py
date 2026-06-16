"""Security helpers for secrets handling, outbound calls, and DSL evaluation.

Outbound URL checks are demo-grade guardrails only: they block obvious private IP
literals and known metadata hostnames, but do not resolve DNS and cannot prevent
SSRF to internal hostnames.
"""

from __future__ import annotations

import ipaddress
import os
import re
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlparse

from simpleeval import SimpleEval

BLOCKED_OUTBOUND_HOSTS = frozenset(
    {
        "metadata.google.internal",
        "169.254.169.254",
    }
)

_SENSITIVE_NAME = re.compile(
    r"^(authorization|x-api-key|api-key|api_key|x-auth-token|secret|token|password)$",
    re.IGNORECASE,
)
_PLACEHOLDER_PATTERN = re.compile(r"%([^%]+)%")
_SENSITIVE_KV_PATTERN = re.compile(
    r'(?i)(["\']?(?:api[_-]?key|secret|token|password|authorization)["\']?\s*[:=]\s*)'
    r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[^"\')\s,]+)'
)


def _contains_sensitive_placeholder(text: str) -> bool:
    for match in _PLACEHOLDER_PATTERN.finditer(text):
        if _is_sensitive_name(match.group(1).strip()):
            return True
    return False


def _redact_sensitive_kv_strings(text: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        prefix = match.group(1)
        value = match.group(2)
        if value and value[0] in "\"'":
            quote = value[0]
            return f"{prefix}{quote}[REDACTED]{quote}"
        return f"{prefix}[REDACTED]"

    return _SENSITIVE_KV_PATTERN.sub(replacer, text)


def has_bearer_token_value(token: Optional[str]) -> bool:
    return bool(token and str(token).strip())


def resolve_bearer_token_for_persist(
    existing: Optional[str],
    incoming: Optional[str],
) -> Optional[str]:
    """Keep the stored token when the client omits or clears the write field."""
    if incoming is None:
        return existing
    if isinstance(incoming, str) and not incoming.strip():
        return existing
    return incoming.strip()


def admin_signal_secret_fields(bearer_token: Optional[str]) -> Dict[str, bool]:
    return {"has_bearer_token": has_bearer_token_value(bearer_token)}


def redact_template_for_response(template: Optional[str]) -> Optional[str]:
    if template is None or template == "":
        return template
    redacted_lines = []
    for line in template.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            if _SENSITIVE_NAME.match(key.strip()) or _looks_like_secret_value(value.strip()):
                redacted_lines.append(f"{key.strip()}: [REDACTED]")
                continue
        redacted_lines.append(_redact_sensitive_kv_strings(line))
    return "\n".join(redacted_lines)


def contains_embedded_credential(template: Optional[str]) -> bool:
    if not template or not template.strip():
        return False
    if _contains_sensitive_placeholder(template):
        return True
    for line in template.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            if _SENSITIVE_NAME.match(key.strip()) or _looks_like_secret_value(value.strip()):
                return True
        if _SENSITIVE_KV_PATTERN.search(line):
            return True
    return False


def _looks_like_secret_value(value: str) -> bool:
    if not value:
        return False
    return value.lower().startswith("bearer ")


def _is_sensitive_name(name: str) -> bool:
    return bool(_SENSITIVE_NAME.match((name or "").strip()))


def _redact_sensitive_value(value: Any) -> Any:
    if value is None:
        return value
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if _looks_like_secret_value(stripped):
        return "[REDACTED]"
    redacted = redact_template_for_response(value)
    if redacted != value:
        return redacted
    redacted = _redact_sensitive_kv_strings(value)
    return redacted if redacted != value else value


def redact_param_map_for_response(param_map: Mapping[str, Any]) -> Dict[str, Any]:
    redacted: Dict[str, Any] = {}
    for key, value in param_map.items():
        if _is_sensitive_name(key):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = _redact_sensitive_value(value)
    return redacted


def validate_outbound_signal_url(url: str) -> None:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL must include a host.")
    if host in BLOCKED_OUTBOUND_HOSTS:
        raise ValueError(f"Outbound URL host not allowed: {host}")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return
    if ip.is_loopback:
        return
    if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        raise ValueError(f"Outbound URL host not allowed: {host}")


def create_restricted_evaluator(names: Mapping[str, Any]) -> SimpleEval:
    evaluator = SimpleEval()
    evaluator.names = dict(names)
    evaluator.functions = {}
    return evaluator


def is_local_mock_client(host: Optional[str]) -> bool:
    if not host:
        return False
    normalized = host.lower()
    if normalized in {"127.0.0.1", "::1", "localhost"}:
        return True
    allow = os.environ.get("DECISION_ENGINE_MOCK_ALLOW_HOSTS", "")
    return normalized in {item.strip().lower() for item in allow.split(",") if item.strip()}
