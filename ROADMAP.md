# Roadmap

Working prototype — not production-ready.

## Current capabilities

- Multi-tenant checkpoints and signals with DSL evaluation (`simpleeval`)
- Auth-derived runtime tenancy; caller-supplied tenant rejected
- Current-version resolution for checkpoints and signals
- Decision audit logging (`decision_log`, `signal_log`, `signal_log_values`)
- Demo bearer auth via environment JSON only (no committed tokens)
- Admin UI for CRUD, tenant copy, and test decisions
- Docker Compose local bootstrap with loopback binding
- Pytest coverage for auth, tenancy, security redaction, and admin hygiene
- OpenAPI at `/docs` (hand-maintained YAML removed)

## Known limitations (demo)

- Bearer tokens are local demo credentials, not production identity
- Signal bearer tokens stored plaintext in Postgres; reads redacted
- Outbound URL checks block obvious private IPs/metadata hosts only — not full SSRF protection
- `/mock/*` restricted to localhost
- Per-process in-memory cache only
- Fixed ~5s HTTP client timeout; `can_run_in_parallel` not enforced
- Admin routes use legacy in-place updates for some config changes

## Near-term hardening (showcase)

- [x] Template and param-value redaction on all read paths
- [x] Tenant copy without secret transfer; associations by signal name
- [x] UI signal types aligned with backend endpoint types
- [x] Structured admin UI notifications (replacing raw `alert()`)
- [x] CI: pytest + smoke on push/PR
- [ ] Admin mutation response contract normalization
- [ ] Further UI modularization (split monolithic admin files)
- [ ] Curate sample SQL fixtures

## Production gaps (out of scope for demo)

- Real identity provider integration
- Secret manager + encryption at rest
- DNS-aware SSRF controls
- Per-signal/checkpoint timeout enforcement
- `can_run_in_parallel` scheduling
- Immutable config writes (version-on-write for checkpoints/signals)
- Structured audit with `actor_id` on all mutations
- Browser/E2E test suite

## Immutable config writes (next backend milestone)

Deferred until showcase repo hygiene is complete:

- POST creates new checkpoint/signal versions; PUT restricted or metadata-only
- Upstream checkpoint copies reference prior signal row IDs
- Copy `signal_variable_values` on signal version create
- UI save paths use one versioning flow
- Transactional writes with pytest coverage
