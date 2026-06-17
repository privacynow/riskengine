# Execution planner

Deterministic vendor-cost containment for checkpoint decisions.

## Model

Runtime clients invoke a checkpoint; operators configure execution policy in admin. The engine:

1. Builds a **dependency graph** from checkpoint DSL and expression signal bodies (associated signals only).
2. Computes the **execution set**: DSL closure plus `always_run_audit` signals.
3. Orders work by **stage → criticality → priority → cost → name**.
4. Skips expensive vendors on **terminal decline** paths unless `vendor_audit_after_decline` is set.
5. Applies **checkpoint** and **tenant period** budgets (priority-first under cap).
6. Resolves structured **outcomes** with per-signal execution status.

## Outcomes

| Outcome | Meaning |
|---------|---------|
| `APPROVE` | Required policy path complete and passed (`degraded: true` if preferred/optional gaps) |
| `DECLINE` | Policy evidence supports decline |
| `REFER` | Review warranted (budget, vendor failure under refer policy) |
| `INCOMPLETE` | Required policy path not evaluable |
| `ERROR` | Engine/system failure |

## Signal execution status

`ran`, `skipped_budget`, `skipped_condition`, `skipped_dependency`, `not_applicable`, `not_evaluated`, `failed`

## Cost accounting

Per decision and per signal:

- `estimated_cost_units` — planning / worst-case
- `reserved_cost_units` — budget reserved at attempt
- `actual_cost_units` — charged spend (`0` on cache hit)
- `cache_hit` — boolean

Cost values are **abstract units** (operator-defined). `billable_event`: `success`, `attempt`, `never`.

## Budgets

- **Checkpoint** `max_cost`: `null` = unlimited, `0` = free signals only, `>0` = cap
- **Tenant** `tenant_budgets`: configurable window (default anchored 30 days)

## Association policy (`checkpoint_signals`)

- `criticality`: `required` | `preferred` | `optional`
- `execution_role`: `referenced_policy` | `always_run_audit` | `manual_test_only`
- `priority_override`, `stage_override`, `vendor_audit_after_decline`

## API response

`POST /decisions` and `POST /ui/test_decisions` return `decision_outcome`, `decision_reason`, `degraded`, `cost` summary, and `signals[]` execution plan.

Test Lab may pass `includeManualTest` and audited `budgetOverride`.
