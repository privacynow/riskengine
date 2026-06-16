"""Canonical signal type contract."""

from __future__ import annotations

from fastapi import HTTPException

SIGNAL_TYPES = frozenset(
    {
        "internal_endpoint",
        "external_endpoint",
        "function",
        "expression",
        "variable",
    }
)


def normalize_signal_type(signal_type: str) -> str:
    normalized = (signal_type or "").strip()
    if normalized not in SIGNAL_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid signal type. Allowed values: "
                + ", ".join(sorted(SIGNAL_TYPES))
            ),
        )
    return normalized
