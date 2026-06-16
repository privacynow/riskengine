# DSL Authoring Guide

Checkpoint `dsl_expression` values are evaluated with **SimpleEval** after the linked signals run. Configured signal names become variables in the expression, and the expression result becomes the final decision value.

This document describes the **current runtime contract**. It intentionally does not list target-state features that are not implemented yet.

## Example

If a checkpoint links signals named `age_check`, `blocklist_check`, and `kyc_score`, the checkpoint DSL can reference those names directly:

```python
age_check and not blocklist_check and (kyc_score > 80)
```

After signals run, their coerced values populate the DSL environment. The final result should typically be `True` or `False`.

## Current allowed syntax

- **Logical:** `and`, `or`, `not`
- **Comparison:** `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Arithmetic:** `+`, `-`, `*`, `/`, `//`, `**`, `%`
- **Grouping:** parentheses
- **Booleans:** `True`, `False`
- **Numbers:** integer and decimal literals
- **Strings:** `'text'` or `"text"`
- **Names:** linked signal names and supplied context variables that are valid Python-style identifiers

## Current restrictions

- **Function calls are not enabled.** The runtime clears the SimpleEval function map, so expressions such as `max(10, credit_score)` are rejected today.
- DSL names are identifiers, not template placeholders. Use `credit_score`, not `%credit_score%`.
- Signal names used in DSL should be stable, snake_case identifiers. Names with spaces or punctuation are not valid DSL variables.
- The runtime currently discovers invalid DSL at evaluation time; a dedicated validation endpoint is target-state work in [ROADMAP.md](ROADMAP.md).

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
- Run the flow in **Test Lab** before promoting checkpoint versions.
- Treat any DSL runtime error as a failed decision path until validation is implemented.
