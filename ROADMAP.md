# Roadmap

This project is a working prototype, not production-ready software.

## Milestone 1 (bootstrap + public repo hygiene) — complete

- Repo hygiene, schema alignment, Docker bootstrap, smoke test, demo mocks, initial commit
- README/runtime claims aligned with actual behavior; admin UI assets vendored locally; deployment docs added

---

## Milestone 2 (runtime correctness + showcase readiness) — in progress

### 2A — Fix Step A semantics — complete

- [x] Auth-derived tenant for runtime APIs (`auth.py`, bearer tokens)
- [x] Reject caller-supplied `tenant_id` / `tenant_name` on runtime routes
- [x] Strict current-signal resolution (no COALESCE fallback to stale rows)
- [x] Smoke tests for 401, 403, cross-tenant same-name checkpoints, inactive signals

### 2B — Minimal showcase auth — complete

- [x] `get_auth_context()` with env-configured bearer tokens (no committed defaults)
- [x] Protect `/decisions`, `/checkpoints/{name}`, `/signals/{name}`, `/ui/*`
- [x] OpenAPI `BearerAuth` security scheme

### 2C — Tier 1 showcase cleanup — largely complete

- [x] Remove merge artifacts (`// ... existing code ...`)
- [x] Product name **Decision Engine** in UI title and README
- [x] README / ROADMAP synced with auth-derived tenancy
- [x] Remove duplicate legacy signal-create modal; unify search save to POST `/ui/signals`
- [x] Remove stale hand-maintained `api/*.yml`; document `/docs` as source of truth
- [x] Vendor licenses in `ui/vendor/LICENSES.md`

### 2D — Small structural pass — complete

- [x] Split `main.py` into `auth`, `db`, `models`, `services/*`, `routes/*`, `demo/mocks`
- [x] `db_cursor()` context manager for new code paths
- [x] Named dataclass mappers in `services/tenancy.py`
- [x] Pydantic v2 `model_dump` in admin routes
- [x] Replace broad bare `except:` in signal invocation paths

### 2E — Tests before more features — complete

- [x] `pytest` for auth tokens, tenant rejection, checkpoint/signal resolution, inactive signals
- [x] `scripts/smoke_test.sh` extended for auth scenarios

### 2F — Immutable checkpoint/signal writes (Step B) — deferred

**Start only after Milestone 2A–2E (done).**

- [ ] `POST` creates new signal/checkpoint versions (immutable config)
- [ ] `PUT` restricted, deprecated, or metadata-only
- [ ] Upstream checkpoint copies use the **old** signal id
- [ ] Copy `signal_variable_values` on signal version create
- [ ] UI save paths use one versioning flow
- [ ] Transactional writes with pytest coverage

---

## Milestone 3 (production-adjacent polish)

- Record `actor_id` in audit tables (documented follow-up from 2B)
- CI matrix (lint, pytest, smoke on PR)
- Honor `can_run_in_parallel` and configured per-signal/checkpoint timeouts
- DSL evaluation hardening
- Structured admin UI errors (replace raw `alert()` where practical)

---

## Known limitations (demo)

- Demo bearer tokens only — not production identity
- `DB_PASSWORD` required at startup (generated into `.env.local`)
- Signal bearer tokens stored plaintext in DB; API reads redacted; production would use a secret manager
- Postgres bound to `127.0.0.1:5432`; password generated with demo env script
- `/mock/*` endpoints restricted to localhost
- In-memory cache is per-process only
- Admin routes still use legacy in-place `PUT` (immutable writes are 2F)
