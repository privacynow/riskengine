"""Single DSL contract for validation and runtime evaluation."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from simpleeval import SimpleEval

BindingMode = Literal["strict", "warn_unknown", "syntax_only"]

_DSL_KEYWORDS = frozenset({"and", "or", "not", "True", "False", "None"})
_IDENTIFIER_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b")

# Allowed constructs must match what evaluate_expression() accepts via SimpleEval
# with functions disabled. List/tuple literals, subscripts, and ternary expressions
# are intentionally excluded from both paths.
_ALLOWED_AST_TYPES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.UAdd,
    ast.USub,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.Compare,
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
    ast.Name,
    ast.Constant,
    ast.Load,
)

_DISALLOWED_AST_TYPES = (
    ast.Call,
    ast.Attribute,
    ast.Subscript,
    ast.Lambda,
    ast.IfExp,
    ast.Dict,
    ast.Set,
    ast.List,
    ast.Tuple,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.Await,
    ast.Yield,
    ast.NamedExpr,
    ast.FormattedValue,
    ast.JoinedStr,
)


@dataclass(frozen=True)
class DslValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": list(self.errors), "warnings": list(self.warnings)}


def extract_dsl_identifiers(expression: str) -> set[str]:
    tokens = _IDENTIFIER_RE.findall(expression)
    return {token for token in tokens if token not in _DSL_KEYWORDS}


def _collect_ast_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in _DSL_KEYWORDS:
            names.add(node.id)
    return names


def _validate_allowed_ast(node: ast.AST) -> None:
    if isinstance(node, _DISALLOWED_AST_TYPES):
        raise ValueError(f"Disallowed expression construct: {type(node).__name__}")
    if not isinstance(node, _ALLOWED_AST_TYPES):
        raise ValueError(f"Disallowed expression construct: {type(node).__name__}")
    for child in ast.iter_child_nodes(node):
        _validate_allowed_ast(child)


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

    try:
        _validate_allowed_ast(tree)
    except ValueError as exc:
        return DslValidationResult(False, [str(exc)], warnings)

    if binding_mode == "syntax_only":
        return DslValidationResult(True, errors, warnings)

    known = {name for name in (known_names or []) if name}
    referenced = _collect_ast_names(tree)
    unknown = referenced - known
    if unknown:
        message = "Unknown identifiers: " + ", ".join(sorted(unknown))
        if binding_mode == "warn_unknown":
            warnings.append(message)
        else:
            errors.append(message)

    return DslValidationResult(not errors, errors, warnings)


def evaluate_expression(expression: str, values: Mapping[str, Any]) -> Any:
    validation = validate_expression(expression, binding_mode="syntax_only")
    if not validation.ok:
        message = validation.errors[0] if validation.errors else "Invalid DSL expression."
        raise ValueError(message)

    evaluator = SimpleEval()
    evaluator.names = dict(values)
    evaluator.functions = {}
    return evaluator.eval(expression)


def binding_mode_for_expression_kind(
    expression_kind: str,
    binding_mode: BindingMode | None = None,
) -> BindingMode:
    if binding_mode is not None:
        return binding_mode
    if expression_kind == "signal_expression":
        return "warn_unknown"
    return "strict"
