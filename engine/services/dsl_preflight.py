"""Backward-compatible preflight entry points."""

from __future__ import annotations

from typing import Any, Sequence

from ..db import db_cursor
from .dsl import (
    BindingMode,
    binding_mode_for_expression_kind,
    extract_dsl_identifiers,
    validate_expression,
)


def list_checkpoint_linked_signal_names(checkpoint_id: str) -> list[str]:
    """Distinct signal names linked to a checkpoint (preflight binding set)."""
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT DISTINCT s.name
              FROM checkpoint_signals cs
              JOIN signals s ON s.id = cs.signal_id
             WHERE cs.checkpoint_id = %s
             ORDER BY s.name
            """,
            (checkpoint_id,),
        )
        return [row[0] for row in cur.fetchall()]


def preflight_dsl(
    expression: str,
    signal_names: Sequence[str] | None = None,
    *,
    binding_mode: BindingMode | None = None,
    expression_kind: str = "checkpoint",
    known_names: Sequence[str] | None = None,
    cycle_check_signals: Sequence[dict[str, str]] | None = None,
) -> dict[str, Any]:
    names = list(signal_names or []) + list(known_names or [])
    mode = binding_mode_for_expression_kind(expression_kind, binding_mode)
    result = validate_expression(expression, names, mode).as_dict()
    if cycle_check_signals and expression_kind == "checkpoint":
        from .execution_planner import DependencyCycleError, validate_checkpoint_dependency_graph

        try:
            validate_checkpoint_dependency_graph(
                expression,
                cycle_check_signals,
            )
        except DependencyCycleError as exc:
            result["ok"] = False
            result["errors"] = list(result.get("errors", [])) + [str(exc)]
    return result
