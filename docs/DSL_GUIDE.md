# DSL Authoring Guide

Checkpoint `dsl_expression` values are evaluated with **SimpleEval**, a safe subset of Python syntax. Configured signal names become variables in the expression.

## Example

If a checkpoint has signals `age_check`, `blocklist_check`, and `kyc_score`:

```python
age_check and not blocklist_check and (kyc_score > 80)
```

After signals run, their values populate the DSL environment. The final result should typically be `True` or `False`.

## Allowed operations

- **Logical:** `and`, `or`, `not`
- **Comparison:** `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Arithmetic:** `+`, `-`, `*`, `/`, `//`, `**`, `%`
- **Grouping:** parentheses
- **Booleans:** `True`, `False`
- **Functions:** `max()`, `min()`, `abs()`, `round()`, `sum()`, `len()`
- **Strings:** `'text'` or `"text"`

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

Built-in function:

```python
max(10, credit_score)
```

## Signal placeholders

Some signals use template placeholders (for example `%user_ssn%`). Set those before evaluation. Once a signal runs, only its **result** appears in the DSL under the signal name—not the placeholder tokens.

## Tips

- Use parentheses for clarity: `(credit_score > 70) and (not blocklist_check)`
- Keep expressions short; prefer readable combinations over deep nesting
- Validate behavior in **Test decisions** before promoting checkpoint versions
