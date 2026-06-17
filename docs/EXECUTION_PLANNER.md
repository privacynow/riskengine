# Execution planner

Deterministic vendor-cost containment for checkpoint decisions.

## Model

Runtime clients invoke a checkpoint; operators configure execution policy in admin. The engine:

1. Builds a **dependency graph** from checkpoint DSL and expression signal bodies (associated signals only).
2. Computes the **execution set**: DSL closure plus `always_run_audit` signals.
3. Orders work by **stage → criticality → priority → cost → name**.
4. Skips expensive vendors on **terminal decline** paths unless `vendor_audit_after_decline` is set.
5. Applies **checkpoint** (in-decision) and **tenant period** (DB-atomic) budgets.
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

- `estimated_cost_units` — planning / worst-case for the full execution set (dependency closure)
- `reserved_cost_units` — cumulative worst-case reserved at admission (does not drop to zero after signals complete)
- `actual_cost_units` — charged spend (`0` on cache hit)
- `cache_hit` — boolean

Cost values are **abstract units** (operator-defined). `billable_event`: `success`, `attempt`, `never`.

## Budgets

### Checkpoint `max_cost`

Enforced in-memory per decision via `BudgetTracker` + `admit_signals_under_budget()`:

- `null` = unlimited
- `0` = free signals only
- `>0` = cap; parallel batches admit greedily in planner order without overspending

### Tenant `tenant_budgets`

Commercial-grade containment uses **atomic DB leases** before vendor calls:

1. `lease_tenant_budget_units()` — `UPDATE … WHERE used + reserved + cost <= limit` (commits before invoke)
2. `finalize_tenant_budget_signal()` — release lease headroom and charge `actual_cost_units` after each signal
3. Tenants without a `tenant_budgets` row are uncapped at tenant level

`reserved_units` on `tenant_budgets` tracks in-flight leases across concurrent decisions. Response `tenant_budget_remaining_units` is reloaded from the ledger after the run.

Test Lab `budgetOverride` skips DB leases and applies spend at persist with audit (`action=budget_override`, `source=test_lab`). `overrideReason` is required.

## Association policy (`checkpoint_signals`)

- `criticality`: `required` | `preferred` | `optional`
- `execution_role`: `referenced_policy` | `always_run_audit` | `manual_test_only`
- `priority_override`, `stage_override`, `vendor_audit_after_decline`

## API response

`POST /decisions` and `POST /ui/test_decisions` return `decision_outcome`, `decision_reason`, `degraded`, `cost` summary, and `signals[]` execution plan.

Historical `GET /decisions/{id}` includes planner outcome fields and per-signal `execution_status`, skip reasons, and cost units.

Test Lab may pass `includeManualTest` and audited `budgetOverride`.
