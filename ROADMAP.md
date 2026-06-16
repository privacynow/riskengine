# Roadmap

Working prototype — not production-ready.

## Current capabilities

- Multi-tenant checkpoints and signals with DSL evaluation (`simpleeval`)
- Auth-derived runtime tenancy; caller-supplied tenant rejected
- Current-version resolution for checkpoints and signals
- Decision audit logging (`decision_log`, `signal_log`, `signal_log_values`)
- Demo bearer auth via environment JSON only (no committed tokens)
- Admin UI: Vue 3 + TypeScript + Vite + Pinia + Vue Router (`ui/`)
- Admin UI tenant scoping via URL `?tenant=` and `tenant_id` on `/ui/*` list/search calls
- Docker Compose local bootstrap with loopback binding
- Pytest coverage for auth, tenancy, security redaction, and admin hygiene
- CI: frontend typecheck/lint/unit/build, pytest, API smoke, UI smoke, Playwright e2e
- OpenAPI at `/docs` (hand-maintained YAML removed)

## Known limitations (demo)

- Bearer tokens are local demo credentials, not production identity
- Signal bearer tokens stored plaintext in Postgres; reads redacted
- Outbound URL checks block obvious private IPs/metadata hosts only — not full SSRF protection
- `/mock/*` restricted to localhost
- Per-process in-memory cache only
- Fixed ~5s HTTP client timeout; `can_run_in_parallel` not enforced
- Admin routes use legacy in-place updates for some config changes
- Admin UI has no version history/compare UX (backend still mutates rows in place)

## Near-term hardening (showcase)

- [x] Template and param-value redaction on all read paths
- [x] Tenant copy without secret transfer; associations by signal name
- [x] UI signal types aligned with backend endpoint types
- [x] Structured admin UI notifications (replacing raw `alert()`)
- [x] CI: pytest + API smoke on push/PR
- [x] Runtime Docker image: Python-only (whitelist COPY; no Node artifacts)
- [x] Admin UI: Vue 3 + TypeScript + Pinia + Router under `ui/src/`
- [x] Admin UI tenant lifecycle (deep links, auth bootstrap, tenant switch reload)
- [x] Browser smoke (`scripts/ui_smoke.sh`) and Playwright e2e (`ui/src/tests/e2e/`, CI)
- [x] Frontend quality gates in CI (typecheck, lint, vitest, build)
- [x] Admin mutation response contract normalization (`ok`, `action`, `id`)
- [x] Curate sample SQL fixtures (`sql/README.md`, section map in seed file)

## Production gaps (out of scope for demo)

- Real identity provider integration
- Secret manager + encryption at rest
- DNS-aware SSRF controls
- Per-signal/checkpoint timeout enforcement
- `can_run_in_parallel` scheduling
- Immutable config writes (version-on-write for checkpoints/signals)
- Structured audit with `actor_id` on all mutations

## Immutable config writes (next backend milestone)

Deferred until showcase repo hygiene is complete:

- POST creates new checkpoint/signal versions; PUT restricted or metadata-only
- Upstream checkpoint copies reference prior signal row IDs
- Copy `signal_variable_values` on signal version create
- UI save paths use one versioning flow
- Transactional writes with pytest coverage
