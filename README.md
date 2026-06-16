## System Overview

**Decision Engine** is a multi-tenant prototype for configurable checkpoint evaluation. Checkpoints combine signals (HTTP calls, local functions, variables, expressions) and a DSL expression to produce a pass/fail outcome with audit logging.

1. Receives `POST /decisions` with a `checkpoint_name` (tenant comes from auth, not the request body).
2. Loads the **current** checkpoint via `checkpoint_current_version`.
3. Resolves linked signals through **current** `signal_current_version` pointers only (no fallback to stale rows).
4. Invokes signals in `order_of_evaluation` order. Same-order signals run sequentially under cost limits, or concurrently when `override_cost_flag` is true.
5. Evaluates the checkpoint DSL with `simpleeval`.
6. Logs to `decision_log` / `signal_log`.

**Cost limits:** When `override_cost_flag` is false, same-order signals run sequentially and cumulative cost is checked before each signal. When `override_cost_flag` is true, same-order signals may run concurrently without cost gating.

**Not yet implemented:** Per-signal HTTP timeouts beyond a fixed 5s client default, `can_run_in_parallel` enforcement, immutable config writes.

> **Status:** Working prototype. See [ROADMAP.md](ROADMAP.md) and [docs/DESIGN_NOTES.md](docs/DESIGN_NOTES.md).

---

## Architecture

FastAPI app split into modules:

| Module | Role |
|--------|------|
| `auth.py` | Bearer token validation (env-configured only) |
| `db.py` | Postgres connection helper |
| `models.py` | Pydantic request/response models |
| `services/decision.py` | Decision orchestration |
| `services/tenancy.py` | Current checkpoint/signal resolution |
| `routes/runtime.py` | `/decisions`, `/checkpoints`, `/signals` |
| `routes/admin.py` | `/ui/*` admin CRUD |
| `demo/mocks.py` | `/mock/*` stub endpoints (hidden from OpenAPI) |

OpenAPI (including `BearerAuth`) is at `/docs`.

---

## Authentication

All runtime and admin routes require `Authorization: Bearer <token>`.

**No production or demo bearer token values are committed in app source, seed data, or Docker images.** Configure auth via environment. Obvious fake tokens exist only in `tests/conftest.py` for pytest.

| Variable | Purpose |
|----------|---------|
| `DECISION_ENGINE_AUTH_TOKENS` | JSON map of bearer token → `{ tenant_id, actor_id, roles }` |
| `DECISION_ENGINE_AUTH_TOKENS_FILE` | Path to a JSON file with the same structure |

The app **fails startup** if neither is set.

### Local demo bootstrap

**Run this before first `docker compose up`.** The app fails startup without auth and database credentials.

```sh
bash scripts/create_demo_env.sh
```

This writes **ignored**, **`chmod 600`** files:

| File | Purpose |
|------|---------|
| `.env.local` | `DB_PASSWORD`, `POSTGRES_PASSWORD`, smoke-test token vars |
| `auth.tokens.local.json` | Bearer token map (mounted into the container, not baked into the image) |

The script prints the **admin bearer token once** — paste it into the `/admin/` login prompt. Runtime tokens are not shown and never reach the browser; the admin UI runs test decisions via `POST /ui/test_decisions`.

Re-running `create_demo_env.sh` **preserves an existing `DB_PASSWORD`** but **rotates auth tokens**. Use a fresh admin token after each run.

**If Postgres auth fails** (for example after a first run that generated a new password against an old volume):

```sh
docker compose down -v
bash scripts/create_demo_env.sh
docker compose up -d --build
```

Or use the clean-room helper: `bash scripts/bootstrap_smoke.sh` (destroys the DB volume, generates env if missing, runs smoke tests).

Runtime clients **must not** send `tenant_id` or `tenant_name`; attempting to do so returns `403`.

See [api/README.md](api/README.md) for token JSON shape.

---

## UI and Admin API

Vue 3 + Vite compiled admin UI at **`/admin/`** (static assets from `ui/dist/`, built in Docker or via `cd ui && npm ci && npm run build`). The UI is a **local demo shell**: it prompts for an admin bearer token from your generated `.env.local` (stored in `sessionStorage` only). Admin JSON API under **`/ui/...`**.

---

## Database

PostgreSQL (`risk_engine_db` in Docker Compose). Schema: [`sql/01_schema.sql`](sql/01_schema.sql). Sample data: [`sql/02_sample_data.sql`](sql/02_sample_data.sql).

---

## Quick Start (Docker)

```sh
git clone <your-repo-url>
cd decision-engine
bash scripts/create_demo_env.sh   # required before first boot
docker compose up -d --build
open http://localhost:8000/admin/ # paste admin token from script output
bash scripts/smoke_test.sh
```

Compose binds the app to **`127.0.0.1:8000`** and Postgres to **`127.0.0.1:5432`** (local demo only).

Clean-room bootstrap (destroys DB volume, generates env if missing):

```sh
bash scripts/bootstrap_smoke.sh
```

Example runtime decision (use `SMOKE_SAMPLE_TOKEN` from `.env.local`):

```sh
set -a && source .env.local && set +a
curl -s -X POST http://localhost:8000/decisions \
  -H "Authorization: Bearer ${SMOKE_SAMPLE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_name":"Onboarding","applicant_id":"demo-1","correlation_id":"demo"}'
```

Run pytest inside the app container (integration tests need Postgres):

```sh
docker compose exec -e RUN_INTEGRATION_TESTS=1 risk-engine pytest -q
```

---

## Local Development (without Docker)

1. Start PostgreSQL and create `risk_engine_db`.
2. Apply `sql/01_schema.sql`, then `sql/02_sample_data.sql`.
3. `bash scripts/create_demo_env.sh` and `set -a && source .env.local && set +a`
4. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
5. `uvicorn main:app --host 0.0.0.0 --port 8000`

---

## Security (demo limitations)

- Bearer tokens are local demo credentials only — not production identity.
- Never commit `.env.local`, `auth.tokens.local.json`, or real token values.
- Connector auth belongs in the `bearer_token` field only — not in header/body templates. API reads redact credentials (`has_bearer_token`, masked template lines).
- Copied tenants get signals with **no** bearer token; re-enter integration secrets per tenant.
- Outbound URL checks block obvious private IPs and metadata hosts only — not full SSRF protection.
- `/mock/*` endpoints accept requests from localhost only.
- Do not expose an instance to the public internet without real auth and secrets management.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md).

---

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## License

MIT — see [LICENSE](LICENSE).
