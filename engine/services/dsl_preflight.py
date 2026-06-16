"""Syntax and identifier binding preflight for checkpoint decision DSL."""

from __future__ import annotations

import ast
import re
from typing import Any, Sequence

_DSL_KEYWORDS = frozenset({"and", "or", "not", "True", "False", "None"})
_IDENTIFIER_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b")

_ALLOWED_AST_TYPES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Name,
    ast.Constant,
    ast.Load,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
)


def extract_dsl_identifiers(expression: str) -> set[str]:
    tokens = _IDENTIFIER_RE.findall(expression)
    return {token for token in tokens if token not in _DSL_KEYWORDS}


def _collect_ast_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id not in _DSL_KEYWORDS:
                names.add(node.id)
    return names


def _validate_allowed_ast(node: ast.AST) -> None:
    if not isinstance(node, _ALLOWED_AST_TYPES):
        raise ValueError(f"Disallowed expression construct: {type(node).__name__}")
    for child in ast.iter_child_nodes(node):
        _validate_allowed_ast(child)


def preflight_dsl(
    expression: str,
    signal_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    expr = (expression or "").strip()
    if not expr:
        return {"ok": False, "errors": ["DSL expression is empty."], "warnings": warnings}

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        errors.append(f"Syntax error: {exc.msg}")
        return {"ok": False, "errors": errors, "warnings": warnings}

    try:
        _validate_allowed_ast(tree)
    except ValueError as exc:
        errors.append(str(exc))
        return {"ok": False, "errors": errors, "warnings": warnings}

    known = {name for name in (signal_names or []) if name}
    referenced = _collect_ast_names(tree)
    unknown = referenced - known
    if unknown:
        errors.append(
            "Unknown signal identifiers: " + ", ".join(sorted(unknown))
        )

    return {"ok": not errors, "errors": errors, "warnings": warnings}
