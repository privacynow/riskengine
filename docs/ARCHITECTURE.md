# Architecture

Current design decisions for the Decision Engine service and admin console.

## Auth-derived tenancy

Runtime clients authenticate with a bearer token bound to exactly one `tenant_id`. Callers cannot supply `tenant_id` or `tenant_name` in query strings or request bodies; doing so returns `403`. Admin tokens may omit tenant binding and select tenants explicitly in the UI.

This enforces tenant isolation at the API boundary: one runtime token maps to one tenant, with no caller-controlled scope escalation.

## Current-version tables

Checkpoints and signals are versioned rows. `checkpoint_current_version` and `signal_current_version` point at the active row per `(tenant_id, name)`.

Runtime execution resolves signals linked on a checkpoint by **name**, not by stale row IDs. Admin workflows can add new signal versions without rewriting every association immediately. Tenant copy preserves associations the same way.

Promotion to current version is explicit: `POST /ui/checkpoints/{id}/make_current` and `POST /ui/signals/{id}/make_current` require a `promotionReason`, update the current-version pointer, and append a row to `promotion_audit`.

## Connector secrets

Outbound HTTP auth belongs in the signal `bearer_token` column only — not in header/body/url templates. Writes reject embedded credentials and sensitive `%placeholder%` names.

API reads redact templates and historical param values. Copied tenants get `NULL` bearer tokens; operators re-enter integration secrets per tenant.

Secrets are stored in Postgres. Production deployments should use a secret manager and encryption at rest.

## Outbound URL policy

Signal URLs are checked for scheme, obvious private IP literals, and known metadata hostnames. DNS is not resolved; internal hostnames are not blocked. Treat this as a baseline guardrail, not full SSRF protection.

## Decision evaluation

`POST /decisions` loads the current checkpoint, runs linked signals in `order_of_evaluation` order, then evaluates the checkpoint `dsl_expression` with SimpleEval. Results are written to `decision_log` and `signal_log`.

Cost limits apply when `override_cost_flag` is false: same-order signals run sequentially with cumulative cost checks. When `override_cost_flag` is true, same-order signals may run concurrently without cost gating.

## Admin UI

Source: `ui/src/`. Production bundles: `ui/dist/`, served at `/admin/` by `engine/main.py`.

| Topic | Behavior |
|-------|----------|
| Login | Admin bearer token from environment; stored in `sessionStorage` (`decisionEngineAdminToken`) |
| API | All mutations and reads via `/ui/*` with `Authorization: Bearer` |
| Test decisions | `POST /ui/test_decisions` — runtime tokens are not sent to the browser |
| Active tenant | Operator selects a tenant; ID appears in the URL as `?tenant=<uuid>` |
| Scoped fetches | Pinia stores pass `tenant_id` on list/search; no cross-tenant rows in the client |
| Navigation | `routeWithTenant()` preserves `?tenant=` on sidebar and in-app links |
| Deep links | `/admin/<route>?tenant=<uuid>` survives auth bootstrap and loads route data |
| Static assets | SPA fallback for extensionless paths only; missing `.js`/`.css` return `404` |

Stack: Vue 3, TypeScript, Vite, Pinia, Vue Router. Frontend developer guide: [ui/README.md](../ui/README.md).

Do not expose the admin UI to the public internet without real identity, TLS, and network controls.

## Configuration writes

Checkpoint and signal rows are versioned. Some admin update paths still mutate rows in place; new versions are created on fork/copy flows. Save-time promotion is not supported — use explicit promote endpoints with a reason.

For DSL authoring behavior and preflight, see [DSL_GUIDE.md](DSL_GUIDE.md). For API shapes and auth, see [API.md](API.md).
