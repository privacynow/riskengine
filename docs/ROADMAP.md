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
- Rule authoring is possible through checkpoints, signals, DSL text, and promotion, but there is no first-class rule lifecycle yet

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
- Governed rule authoring: drafts, validation, approval, promotion, rollback, and version comparison

## Rule authoring system target state

The commercial product should treat rule authoring as a governed lifecycle, not as raw CRUD over checkpoints and signals. The current model already has the right primitives — tenant-scoped decision flows, signal library, DSL evaluation, test lab, audit log, and current-version pointers — but the target system needs a first-class authoring experience around them.

### Authoring model

- Decision flows are the top-level rule packages exposed to operators.
- Signals remain reusable building blocks: variables, expressions, functions, and endpoint integrations.
- A flow draft owns a DSL expression, linked signals, expected inputs, runtime policy, and test cases.
- A promoted flow version is immutable and is the only version used by runtime `POST /decisions` unless a test explicitly targets a draft/version ID.
- Each tenant owns its own drafts, promoted versions, connector secrets, and audit history.

### Lifecycle

1. Create or clone a decision flow draft.
2. Add or update linked signals.
3. Define expected input parameters and types.
4. Author the DSL expression with validation feedback.
5. Run saved scenario tests in Test Lab.
6. Review a diff against the current promoted version.
7. Promote the draft with an actor, reason, and audit entry.
8. Monitor live decisions and signal failures.
9. Roll back to a prior promoted version if needed.

### Validation and safety

- Parse DSL before save; reject syntax errors with line/column feedback.
- Detect unknown signal names, unlinked signal references, duplicate names, and invalid identifiers.
- Type-check common comparisons when signal/input types are known.
- Validate endpoint templates for missing placeholders and blocked credential fields.
- Prevent promotion when required test cases fail.
- Keep runtime failures fail-closed and visible in audit.

### Versioning and audit

- All config-changing saves create immutable versions.
- PUT is restricted to metadata-only fields or removed from config mutation paths.
- Version history APIs list flow/signal versions with actor, timestamp, reason, status, and diff summary.
- UI exposes compare, promote, rollback, and deactivate actions from a Versions tab.
- Audit records include actor IDs for every admin mutation and promotion.

### Operator experience

- DSL editor shows linked signals, expected inputs, and available variables.
- Autocomplete suggests signal names and supported operators.
- Validation runs inline and in a server-side preflight endpoint.
- Test Lab can run against draft versions before promotion.
- Audit can re-run past scenarios against current, draft, or historical versions.
- Overview surfaces rule health: failing flows, costly flows, untested drafts, stale signals, and recent promotions.

## Immutable config writes (next backend milestone)

- POST creates new checkpoint/signal versions; PUT restricted or metadata-only
- Upstream checkpoint copies reference prior signal row IDs
- Copy `signal_variable_values` on signal version create
- UI save paths use one versioning flow
- Transactional writes with pytest coverage
