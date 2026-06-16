# DSL Authoring Guide

Checkpoint `dsl_expression` values and signal `expression_body` values are evaluated with **SimpleEval** (functions disabled) through the shared module `engine/services/dsl.py`. Preflight and runtime use the same allowlist.

## Checkpoint DSL

After linked signals run, their coerced values populate the DSL environment under each signal **name**. The expression result becomes the final decision value.

Example:

```python
age_check and not blocklist_check and (kyc_score > 80)
```

## Allowed syntax

Both preflight and runtime accept:

- **Logical:** `and`, `or`, `not`
- **Comparison:** `==`, `!=`, `<`, `<=`, `>`, `>=`, `is`, `is not`, `in`, `not in`
- **Arithmetic:** `+`, `-`, `*`, `/`, `//`, `**`, `%`
- **Unary:** `-value`, `not flag`
- **Grouping:** parentheses
- **Literals:** booleans, numbers, strings
- **Names:** identifiers bound in the evaluation context

Use `1 in values` where `values` is a bound name (for example a list supplied at runtime). **Inline list/tuple literals** (`[1,2,3]`, `(1,2,3)`) are not supported.

## Rejected syntax (preflight and runtime)

- Function calls (`max(a, b)`)
- Subscripts (`items[0]`)
- Ternary expressions (`a if flag else b`)
- Attribute access, comprehensions, dict/set literals

## Preflight API

`POST /ui/dsl_preflight`

```json
{
  "dsl_expression": "age_check and mystery_signal",
  "signal_names": ["age_check", "blocklist_check"],
  "expression_kind": "checkpoint",
  "binding_mode": "strict"
}
```

| `expression_kind` | Default `binding_mode` | Unknown identifiers |
|-------------------|------------------------|---------------------|
| `checkpoint` | `strict` | Error |
| `signal_expression` | `warn_unknown` | Warning |

Preflight validates syntax/operators only. It does not evaluate expressions with dummy values.

## Signal expression signals

Expression signals evaluate `expression_body` with a context containing:

1. Results from prior signals in the same decision (`order_of_evaluation`)
2. Request parameters whose names appear as identifiers in `expression_body`
3. Request parameters referenced in endpoint/function templates (unchanged)

Example expression body:

```python
request_score > 10
```

Pass `request_score` in the decision `parameters` map (Test Lab or runtime `POST /decisions`).

## Endpoint placeholders

HTTP/function signals may still use `%placeholder%` syntax in templates. Those are separate from DSL identifiers.

## Authoring tips

- Run **DSL preflight** before saving or promoting checkpoint versions.
- For expression signals, unresolved identifier warnings mean “must be supplied by request params or prior signals.”
- Exercise new versions in **Test Lab** before promotion.
