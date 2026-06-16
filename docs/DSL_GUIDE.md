# DSL Authoring Guide

Checkpoint `dsl_expression` values are evaluated with **SimpleEval** after the linked signals run. Configured signal names become variables in the expression, and the expression result becomes the final decision value.

This document describes the **current** runtime and authoring contract.

## Example

If a checkpoint links signals named `age_check`, `blocklist_check`, and `kyc_score`, the checkpoint DSL can reference those names directly:

```python
age_check and not blocklist_check and (kyc_score > 80)
```

After signals run, their coerced values populate the DSL environment. The final result should typically be `True` or `False`.

## Allowed syntax (runtime)

- **Logical:** `and`, `or`, `not`
- **Comparison:** `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Arithmetic:** `+`, `-`, `*`, `/`, `//`, `**`, `%`
- **Grouping:** parentheses
- **Booleans:** `True`, `False`
- **Numbers:** integer and decimal literals
- **Strings:** `'text'` or `"text"`
- **Names:** linked signal names and supplied context variables that are valid Python-style identifiers

## Restrictions

- **Function calls are not enabled.** The runtime clears the SimpleEval function map, so expressions such as `max(10, credit_score)` are rejected.
- DSL names are identifiers, not template placeholders. Use `credit_score`, not `%credit_score%`.
- Signal names used in DSL should be stable, snake_case identifiers. Names with spaces or punctuation are not valid DSL variables.

## Preflight validation

Before save or promotion, the admin UI and API can validate DSL with:

`POST /ui/dsl_preflight`

Request body:

```json
{
  "dsl_expression": "age_check and mystery_signal",
  "signal_names": ["age_check", "blocklist_check"]
}
```

Response:

```json
{
  "ok": false,
  "errors": ["Unknown signal identifiers: mystery_signal"],
  "warnings": []
}
```

Preflight behavior:

- Rejects empty expressions.
- Parses the expression with Python `ast` in `eval` mode and rejects syntax errors.
- Allows boolean logic, comparisons, names, and constants only — no function calls, attribute access, subscripts, comprehensions, or arithmetic operators.
- Treats unknown identifiers (names not in `signal_names`) as **errors**, not warnings.

Preflight is stricter than runtime evaluation today: expressions with arithmetic may run in Test Lab or production but fail preflight until AST rules expand. Prefer boolean and comparison expressions for checkpoint decisions.

Runtime evaluation applies SimpleEval with functions disabled. Preflight catches most authoring mistakes before a version is saved or promoted. Remaining runtime failures (for example type mismatches during evaluation) surface when a decision runs.

## More examples

Numeric + boolean:

```python
(credit_score >= 70) and eligible
```

Numeric thresholds:

```python
(account_balance > 1000) and (days_overdue <= 5)
```

String comparison:

```python
region == "US"
```

Combining signals:

```python
income_verified and (risk_score < 0.35) and not active_fraud_alert
```

## Signal placeholders

Endpoint and function signals may use template placeholders such as `%user_ssn%` in request templates. Those placeholders are filled before the signal executes. Once a signal runs, only the signal **result** appears in the checkpoint DSL under the signal name.

For example, a signal may use `%user_ssn%` to call an external service, but the checkpoint DSL should reference the resulting signal name:

```python
identity_verified and age_check
```

## Authoring tips

- Use parentheses for clarity: `(credit_score > 70) and (not blocklist_check)`.
- Keep expressions short; prefer readable combinations over deep nesting.
- Prefer expression signals for reusable sub-conditions, then combine their results in the checkpoint DSL.
- Run **DSL preflight** in the checkpoint editor and exercise the flow in **Test Lab** before promoting a version.
- Treat DSL runtime errors during decision execution as a failed decision path until the expression is corrected.
