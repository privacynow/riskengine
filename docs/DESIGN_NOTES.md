# Design Notes

Intentional tradeoffs for this demo prototype. Not production guidance.

## Auth-derived tenancy

Runtime clients authenticate with a bearer token bound to exactly one `tenant_id`. Callers cannot supply `tenant_id` or `tenant_name` in query strings or request bodies; doing so returns `403`. Admin tokens may omit tenant binding and select tenants explicitly in the UI.

This keeps tenant isolation simple for a showcase: one token, one tenant, no caller-controlled scope escalation.

## Current-version tables

Checkpoints and signals are versioned rows. `checkpoint_current_version` and `signal_current_version` point at the active row per `(tenant_id, name)`.

Runtime execution resolves signals linked on a checkpoint by **name**, not by stale row IDs. That allows admin workflows to add new signal versions without rewriting every association immediately. Tenant copy preserves associations the same way.

## Connector secrets

Outbound HTTP auth belongs in the signal `bearer_token` column only — not in header/body/url templates. Writes reject embedded credentials and sensitive `%placeholder%` names.

API reads redact templates and historical param values. Copied tenants get `NULL` bearer tokens; operators re-enter integration secrets per tenant.

Secrets are stored plaintext in Postgres for this demo. Production would use a secret manager and encryption at rest.

## Outbound URL policy

Signal URLs are checked for scheme, obvious private IP literals, and known metadata hostnames. DNS is not resolved; internal hostnames are not blocked. This is a demo guardrail, not SSRF protection.

## Admin UI

Source: `ui/src/`. Production bundles: `ui/dist/`, served at `/admin/` by `engine/main.py`.

| Topic | Behavior |
|-------|----------|
| Login | Admin bearer token from `.env.local`; stored in `sessionStorage` (`decisionEngineAdminToken`) |
| API | All mutations and reads via `/ui/*` with `Authorization: Bearer` |
| Test decisions | `POST /ui/test_decisions` — runtime tokens never sent to the browser |
| Active tenant | Operator selects a tenant; ID appears in the URL as `?tenant=<uuid>` |
| Scoped fetches | Pinia stores pass `tenant_id` on list/search; no cross-tenant rows in the client |
| Navigation | `routeWithTenant()` preserves `?tenant=` on sidebar and in-app links |
| Deep links | `/admin/<route>?tenant=<uuid>` survives auth bootstrap and loads route data |
| Static assets | SPA fallback for extensionless paths only; missing `.js`/`.css` return `404` |

Stack: Vue 3, TypeScript, Vite, Pinia, Vue Router. See [UI_REDESIGN.md](UI_REDESIGN.md) and [../ui/README.md](../ui/README.md).

Do not expose the admin UI to the public internet without real identity, TLS, and network controls.

## Immutable writes (deferred)

Admin routes still use in-place updates for some paths. Immutable version-on-write (POST-only config changes) is planned but deferred until repo hygiene and showcase polish are complete. The UI does not yet expose version history or compare views.
