# DSL Authoring Guide

Checkpoint `dsl_expression` and signal `expression_body` values are evaluated through **SimpleEval** (`simpleeval==0.9.13`) via `engine/services/dsl.py`.

SimpleEval is the DSL authority. Our code configures it with `functions={}` and supplies caller-provided names. Preflight uses the same evaluator for probe checks — there is no separate AST operator allowlist.

## Checkpoint DSL

After linked signals run, their coerced values populate the DSL environment under each signal **name**.

```python
age_check and not blocklist_check and (kyc_score > 80)
```

## Supported syntax (SimpleEval with functions disabled)

- Boolean logic: `and`, `or`, `not`
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`, `is`, `is not`, `in`, `not in`
- Arithmetic: `+`, `-`, `*`, `/`, `//`, `**`, `%`
- Subscripts and mapping access: `items[0]`, `payload["score"]`
- Ternary expressions: `a if flag else b`
- Grouping, literals (booleans, numbers, strings), and bound identifiers

Use `1 in values` where `values` is a bound name. **Inline list/tuple literals** (`[1,2,3]`, `(1,2)`) are not supported by SimpleEval.

## Rejected syntax

- Function calls (`max(a, b)`) — `FunctionNotDefined`
- Imports / dunder access (`__import__`, `obj.__class__`) — blocked by SimpleEval
- Inline list/tuple literals in expressions

## Preflight API

`POST /ui/dsl_preflight`

Preflight steps:

1. Parse syntax with `ast.parse`
2. Extract identifier names from AST `Name` nodes (not string literals)
3. Apply binding mode for unknown identifiers
4. Probe-evaluate with SimpleEval using neutral probe contexts

| `expression_kind` | Default binding | Unknown identifiers |
|-------------------|-----------------|---------------------|
| `checkpoint` | `strict` | Error |
| `signal_expression` | `warn_unknown` | Warning |

## Signal expression context

Expression signals receive:

1. Prior signal results in the same decision
2. Request `parameters` whose names appear as identifiers in `expression_body`

Example: `request_score > 10` with `parameters.request_score`.

## Authoring tips

- Run DSL preflight before save or promote.
- Exercise new versions in Test Lab before promotion.
- Prefer bound names over inline collection literals.
