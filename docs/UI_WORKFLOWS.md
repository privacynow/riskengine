# Admin UI workflows

> **Status:** Operational workbench workflows below are **shipped**. Remaining backlog is mostly the **Versions tab** (history/diff) and backend immutable writes — see [Target-state](#target-state-not-fully-shipped).

Operational workbench for decision flow design, signal configuration, testing, and audit. Every screen should map to one of these workflows.

## Primary workflows

| Workflow | Entry points | Done when |
|----------|--------------|-----------|
| Create a decision flow | Decision Flows → New flow | Named flow with DSL draft saved (version created) |
| Wire signals to a flow | Flow detail → Signals tab | Associations reflect current-version signals |
| Configure signal execution | Signal Library → detail → Configuration | Cost, order, timeout, cache, parallel flag set |
| Promote a version | Flow or Signal list → Promote | `make_current` succeeds; badge shows Current |
| Run a test decision | Test Lab → select flow → Run | Trace shows per-signal outcome for the **selected row** (`checkpoint_id`) |
| Re-run a past scenario | Audit → decision detail → Run similar test | Test Lab opens with flow, IDs, and non-redacted params prefilled |
| Explain a decision | Audit → decision row → detail | Timeline, cost, redacted params, link to flow |
| Investigate failed signal | Audit → Signal logs | Log detail shows error context and links to signal |
| Copy tenant config | Tenants → Create with copy source | New tenant scoped; secrets cleared |

## Navigation (product labels)

| Label | Route | Purpose |
|-------|-------|---------|
| Overview | `/overview` | Tenant health, recent decisions, failure shortcuts |
| Tenants | `/tenants` | Workspace list and edit |
| Decision Flows | `/flows` | Checkpoint-centric builder (alias: `/checkpoints`) |
| Signal Library | `/signals` | Connector/function/variable catalog |
| Relationships | `/associations` | Cross-entity explorer (secondary to in-detail association UI) |
| Test Lab | `/test-lab` | Scenario runner with execution trace (alias: `/test-decisions`) |
| Audit | `/audit/decisions` | Decision and signal log search |

Tenant scope is always `?tenant=<uuid>` on tenant-bound routes.

## Shipped screen patterns

### Master-detail workbench

List pane (left): scan name, type, version badge, cost, secret status.  
Detail pane (right): tabs — Summary, Configuration, Flows/Signals (associations).  
Deep links (`/signals/:id`, `/checkpoints/:id`) fetch detail by ID when the row is not on page 1.

Row click updates route and opens detail. Mobile: list full-width; detail opens beside or below list.

### Forms

- Typed drafts; `v-model` + explicit save.
- Type-specific sections (variable / function / endpoint).
- Secret fields write-only; blank preserves existing token.
- Signal save creates a new version (POST); UI navigates to the new row ID.
- Promote current is a separate action (`make_current`).

### Test Lab

1. Select tenant (URL).
2. Select decision flow row (any version).
3. Parameter form from associated signal placeholders.
4. Run → summary card (decision, cost).
5. Signal trace table.
6. Raw JSON in collapsible inspector (secondary).

Tests pass `checkpoint_id` so the executed DSL matches the selected row.

## Shipped audit explorer

- Master-detail layout with filters: text search, correlation ID, applicant ID, date range (decisions), failures-only (signal logs).
- Decision detail: summary metrics, DSL snapshot, per-signal trace timeline, links to Decision Flows and **Run similar test** (prefills Test Lab via `checkpoint`, `applicant`, `correlation`, `from_decision`).
- Signal log detail: execution outcome, redacted params, links to Signal Library and related decision.

## Target-state *(not fully shipped)*

### Versions tab

Version history, diff, and in-drawer promote/deactivate when backend list APIs exist.

### Audit follow-ups

- *(shipped)* “Run similar test” prefills Test Lab from decision context (`checkpoint`, `applicant`, `correlation`, `from_decision`).

## API gaps (UI backlog)

- Version history list/diff (backend read APIs limited today).
- Variable values list-by-signal (upsert only today).

## Acceptance questions

A reviewer should answer without reading code:

1. What decision flows exist for this tenant?
2. Which version is live?
3. Which signals run, in what order, and at what cost?
4. How is each signal invoked (endpoint templates, expression, variable)?
5. How do I change a flow safely (new version + promote)?
6. How do I test before promoting?
7. How do I explain a past decision?
8. How do I triage a failed signal?
