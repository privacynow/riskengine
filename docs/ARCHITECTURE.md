# Architecture

Current design decisions for the Decision Engine service and admin console.

## Auth-derived tenancy

Runtime clients authenticate with a bearer token bound to exactly one `tenant_id`. Callers cannot supply `tenant_id` or `tenant_name` in query strings or request bodies; doing so returns `403`. Admin tokens may omit tenant binding and select tenants explicitly in the UI.

## Current-version tables

Checkpoints and signals are versioned rows. `checkpoint_current_version` and `signal_current_version` point at the active row per `(tenant_id, name)`.

Runtime execution resolves signals linked on a checkpoint by **name**, not by stale row IDs.

Promotion is explicit and audited: `POST /ui/checkpoints/{id}/make_current` and `POST /ui/signals/{id}/make_current` require `promotionReason`, validate checkpoint DSL where applicable, update the current-version pointer, and append `promotion_audit`.

## DSL contract

All checkpoint DSL and signal expression evaluation goes through `engine/services/dsl.py`:

- `validate_expression()` — preflight (AST allowlist + identifier binding)
- `evaluate_expression()` — runtime (same allowlist, then SimpleEval)

Preflight and runtime reject the same constructs. See [DSL_GUIDE.md](DSL_GUIDE.md).

## Decision evaluation

`POST /decisions` (and admin `POST /ui/test_decisions`):

1. Loads the checkpoint (current or explicit draft ID in Test Lab)
2. Inserts `decision_log` as `PENDING`
3. Runs linked signals grouped by `order_of_evaluation`

### Signal scheduling

Within each order group:

- Signals with `can_run_in_parallel=true` may run concurrently
- Other signals run serially
- `override_cost_flag` controls **cost gating only** (allow over-budget execution), not parallelism

### Timeouts

- `signal.timeout_seconds` caps each signal invocation (`asyncio.wait_for` + HTTP client timeout)
- `checkpoint.timeout_seconds` is a **decision deadline** from the start of execution
- Each signal uses `min(signal.timeout_seconds, remaining_checkpoint_seconds)`
- Parallel batches are wrapped in a checkpoint deadline `wait_for`
- Expired signals log `checkpoint_timeout` or `signal_timeout` in `signal_log.error_message` when present

### Expression signal context

Expression signals receive prior signal results plus request `parameters` whose names appear as DSL identifiers in `expression_body` (and template placeholders for HTTP/function signals).

4. Evaluates checkpoint `dsl_expression`
5. Updates `decision_log` (never left `PENDING` after orchestration completes)

## Configuration writes

| Resource | New version | Metadata update |
|----------|-------------|-----------------|
| Checkpoint | `POST /ui/checkpoints` (optional `signals`, `copyFromCheckpointId`) | `PUT /ui/checkpoints/{id}` — description only |
| Signal | `POST /ui/signals` (optional `copyFromSignalId` copies variable values + checkpoint associations) | `PUT /ui/signals/{id}` — description only |

Save-time promotion is not supported.

## Admin API validation

Path and write-model IDs are validated as UUIDs. Invalid IDs return **422** before database access.

## Connector secrets

Outbound HTTP auth belongs in `signals.bearer_token` only. API reads redact templates and param values. Copied tenants get `NULL` bearer tokens.

## Outbound URL policy

Scheme check, obvious private IP literals, and known metadata hostnames. Not full SSRF protection.

## Admin UI

Source: `ui/src/`. Served at `/admin/`. Active tenant in `?tenant=<uuid>`. Frontend guide: [ui/README.md](../ui/README.md).

## Test fixtures

Visual regression data lives in `tests/fixtures/visual_fixture.sql` and is applied with `scripts/seed_visual_fixture.sh` — not during application startup.
