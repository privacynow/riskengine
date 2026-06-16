"""Encrypt connector credentials at rest."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:v1:"


def _fernet() -> Fernet | None:
    raw = os.environ.get("DECISION_ENGINE_SECRET_ENCRYPTION_KEY", "").strip()
    if not raw:
        return None
    return Fernet(raw.encode("utf-8") if isinstance(raw, str) else raw)


def encryption_enabled() -> bool:
    return _fernet() is not None


def encrypt_secret(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    value = plaintext.strip()
    if not value:
        return None
    fernet = _fernet()
    if fernet is None:
        raise RuntimeError(
            "Cannot store connector secret: DECISION_ENGINE_SECRET_ENCRYPTION_KEY is not set."
        )
    token = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_secret(stored: str | None) -> str | None:
    if stored is None:
        return None
    value = stored.strip()
    if not value:
        return None
    if not value.startswith(_PREFIX):
        return value
    fernet = _fernet()
    if fernet is None:
        raise RuntimeError(
            "Encrypted connector secret found but DECISION_ENGINE_SECRET_ENCRYPTION_KEY is not set."
        )
    try:
        return fernet.decrypt(value[len(_PREFIX) :].encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Failed to decrypt connector secret.") from exc


def redact_stored_secret(stored: str | None) -> str | None:
    if stored is None or not str(stored).strip():
        return stored
    return stored if not str(stored).startswith(_PREFIX) else f"{_PREFIX}[ciphertext]"
