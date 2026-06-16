"""SimpleEval-backed DSL facade for validation and runtime evaluation."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from simpleeval import SimpleEval

BindingMode = Literal["strict", "warn_unknown", "syntax_only"]

_DSL_KEYWORDS = frozenset({"and", "or", "not", "True", "False", "None"})


@dataclass(frozen=True)
class DslValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": list(self.errors), "warnings": list(self.warnings)}


def create_dsl_evaluator(names: Mapping[str, Any]) -> SimpleEval:
    """Return a configured SimpleEval instance — the DSL authority."""
    evaluator = SimpleEval()
    evaluator.names = dict(names)
    evaluator.functions = {}
    return evaluator


def _collect_ast_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in _DSL_KEYWORDS:
            names.add(node.id)
    return names


def extract_dsl_identifiers(expression: str) -> set[str]:
    expr = (expression or "").strip()
    if not expr:
        return set()
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return set()
    return _collect_ast_names(tree)


def _probe_contexts(names: set[str]) -> list[dict[str, Any]]:
    if not names:
        return [{}]
    return [
        {name: 1 for name in names},
        {name: True for name in names},
        {name: [1] for name in names},
        {name: {"k": 1} for name in names},
    ]


def _minimal_probe_context(tree: ast.AST, names: set[str]) -> dict[str, Any]:
    """Build a context shaped for subscripts/attributes found in the expression."""
    context: dict[str, Any] = {name: 1 for name in names}
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            var = node.value.id
            slice_node = node.slice
            if isinstance(slice_node, ast.Constant):
                key = slice_node.value
                if isinstance(key, str):
                    existing = context.get(var)
                    payload = dict(existing) if isinstance(existing, dict) else {}
                    payload[key] = 1
                    context[var] = payload
                elif isinstance(key, int) and key >= 0:
                    length = max(key + 1, 1)
                    context[var] = [1] * length
    return context


def _probe_simpleeval(expression: str, names: set[str], tree: ast.AST) -> str | None:
    """Return an error string when SimpleEval rejects an expression in every probe context."""
    contexts = [_minimal_probe_context(tree, names)]
    contexts.extend(_probe_contexts(names))
    last_error: str | None = None
    for context in contexts:
        try:
            create_dsl_evaluator(context).eval(expression)
            return None
        except Exception as exc:
            last_error = str(exc)
    return last_error


def evaluate_expression(expression: str, values: Mapping[str, Any]) -> Any:
    expr = (expression or "").strip()
    if not expr:
        raise ValueError("DSL expression is empty.")
    return create_dsl_evaluator(values).eval(expr)


def validate_expression(
    expression: str,
    known_names: Sequence[str] | None = None,
    binding_mode: BindingMode = "strict",
) -> DslValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    expr = (expression or "").strip()
    if not expr:
        return DslValidationResult(False, ["DSL expression is empty."], warnings)

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        return DslValidationResult(False, [f"Syntax error: {exc.msg}"], warnings)

    referenced = _collect_ast_names(tree)
    known = {name for name in (known_names or []) if name}

    if binding_mode != "syntax_only":
        unknown = referenced - known
        if unknown:
            message = "Unknown identifiers: " + ", ".join(sorted(unknown))
            if binding_mode == "warn_unknown":
                warnings.append(message)
            else:
                errors.append(message)

    if not errors:
        probe_names = referenced if binding_mode == "syntax_only" else (referenced | known)
        probe_error = _probe_simpleeval(expr, probe_names, tree)
        if probe_error:
            errors.append(probe_error)

    return DslValidationResult(not errors, errors, warnings)


def binding_mode_for_expression_kind(
    expression_kind: str,
    binding_mode: BindingMode | None = None,
) -> BindingMode:
    if binding_mode is not None:
        return binding_mode
    if expression_kind == "signal_expression":
        return "warn_unknown"
    return "strict"
