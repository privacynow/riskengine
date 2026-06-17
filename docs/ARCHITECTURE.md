# Architecture

Current design decisions for the Decision Engine service and admin console.

## Auth-derived tenancy

Runtime clients authenticate with a bearer token bound to exactly one `tenant_id`. Callers cannot supply `tenant_id` or `tenant_name` in query strings or request bodies; doing so returns `403`. Admin tokens may omit tenant binding and select tenants explicitly in the UI.

## Current-version tables

Checkpoints and signals are versioned rows. `checkpoint_current_version` and `signal_current_version` point at the active row per `(tenant_id, name)`.

Runtime resolves linked signals by logical **name** through `signal_current_version`. Execution SQL deduplicates to one current row per signal name even if legacy association rows exist for multiple versions.

Promotion is explicit and audited: `POST /ui/checkpoints/{id}/make_current`, `POST /ui/signals/{id}/make_current`, plus `deactivate` / `reactivate` endpoints. All require `promotionReason` and append `promotion_audit` with `action` (`promote`, `deactivate`, `reactivate`).

## DSL contract

All checkpoint DSL and signal expression evaluation uses `engine/services/dsl.py`:

- `create_dsl_evaluator(names)` — configured `SimpleEval(functions={}, names=names)`
- `evaluate_expression()` — direct SimpleEval evaluation (no custom operator gate)
- `validate_expression()` — AST syntax + identifier binding + SimpleEval probe evaluation

SimpleEval is the language authority. See [DSL_GUIDE.md](DSL_GUIDE.md).

Admin DSL preflight uses the same contract. Existing checkpoint preflight may pass `checkpoint_id`; the server checks tenant access and resolves linked signal names from `checkpoint_signals`. New checkpoint drafts pass selected signal names from the client because no checkpoint row exists yet.

## Decision evaluation

`POST /decisions` (and admin `POST /ui/test_decisions`):

1. Loads the checkpoint (current or explicit draft ID in Test Lab)
2. Runs linked signals grouped by `order_of_evaluation`

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
5. Persists `decision_log`, signal audit rows, and cache writes in one short write transaction after execution completes. Signal HTTP calls run with no write transaction held; cache reads use independent short read connections.

### Signal caching

Signals with `allow_caching=true` read `signal_cached_values` via short read connections. New cache writes are staged in memory and persisted in the final write transaction. The in-memory cache updates only after commit succeeds.

## Configuration writes

| Resource | New version | Metadata update |
|----------|-------------|-----------------|
| Checkpoint | `POST /ui/checkpoints` (optional `signals`, `copyFromCheckpointId`) | `PUT /ui/checkpoints/{id}` — description only |
| Signal | `POST /ui/signals` (optional `copyFromSignalId` copies variable values only) | `PUT /ui/signals/{id}` — description only |

Save-time promotion is not supported.

## Admin API validation

Path and write-model IDs are validated as UUIDs. Invalid IDs return **422** before database access.

## Connector secrets

Outbound HTTP auth belongs in `signals.bearer_token` only. Values are encrypted at rest (`enc:v1:`) when `DECISION_ENGINE_SECRET_ENCRYPTION_KEY` is configured; admin writes with a bearer token fail if the key is missing. API reads redact templates and param values. Copied tenants get `NULL` bearer tokens.

## Outbound URL policy

Scheme check, obvious private IP literals, and known metadata hostnames. Not full SSRF protection.

## Admin UI

Source: `ui/src/`. Served at `/admin/`. Active tenant in `?tenant=<uuid>`. Frontend guide: [ui/README.md](../ui/README.md).

## Test fixtures

Playwright and integration tests use SQL fixtures applied on demand — not during application startup:

| Fixture | File | Purpose |
|---------|------|---------|
| Visual regression | `tests/fixtures/visual_fixture.sql` | Stable `VISUAL FIXTURE BANK` tenant for screenshot tests |
| Lifecycle e2e | `tests/fixtures/lifecycle_e2e_fixture.sql` | Scratch `Lifecycle E2E Checkpoint` for deactivate/reactivate tests |

Both are applied by `scripts/seed_visual_fixture.sh` (CI runs this before Playwright). See [ui/README.md](../ui/README.md) for how specs consume them.
