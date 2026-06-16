"""Backward-compatible preflight entry points."""

from __future__ import annotations

from typing import Any, Sequence

from .dsl import (
    BindingMode,
    binding_mode_for_expression_kind,
    extract_dsl_identifiers,
    validate_expression,
)


def preflight_dsl(
    expression: str,
    signal_names: Sequence[str] | None = None,
    *,
    binding_mode: BindingMode | None = None,
    expression_kind: str = "checkpoint",
    known_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    names = list(signal_names or []) + list(known_names or [])
    mode = binding_mode_for_expression_kind(expression_kind, binding_mode)
    return validate_expression(expression, names, mode).as_dict()
