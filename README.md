# Decision Engine

Multi-tenant checkpoint evaluation: signals + DSL, audit logging, and a Vue admin workbench.

## Repository layout

| Path | What it is |
|------|------------|
| [`ui/`](ui/) | Admin SPA (Vue 3 + TypeScript); built to `ui/dist/`, served at `/admin/` |
| [`routes/`](routes/) | FastAPI routers — runtime (`/decisions`) and admin (`/ui/*`) |
| [`services/`](services/) | Decision engine, tenancy resolution, security, pagination |
| [`sql/`](sql/) | Postgres schema and idempotent demo seed ([`sql/README.md`](sql/README.md)) |
| [`scripts/`](scripts/) | Demo env, smoke tests, Docker helpers |
| [`tests/`](tests/) | Pytest (auth, tenancy, admin hygiene) |
| [`docs/`](docs/) | Roadmap, workflows, API auth notes, deployment |
| `main.py`, `auth.py`, … | App entry and core Python modules (flat layout for this prototype) |
| `Dockerfile`, `docker-compose.yml` | Container build and local stack |

**Docs:** [Roadmap](docs/ROADMAP.md) · [UI workflows](docs/UI_WORKFLOWS.md) · [API auth](docs/API.md) · [Design notes](docs/DESIGN_NOTES.md)

---

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

> **Status:** Working prototype. See [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/DESIGN_NOTES.md](docs/DESIGN_NOTES.md).

---

## Architecture

FastAPI app split into modules:

| Module | Role |
|--------|------|
| `main.py` | App entry, lifespan, `/admin/` static mount with SPA fallback |
| `auth.py` | Bearer token validation (env-configured only) |
| `db.py` | Postgres connection helper |
| `models.py` | Pydantic request/response models |
| `services/decision.py` | Decision orchestration |
| `services/tenancy.py` | Current checkpoint/signal resolution |
| `routes/runtime.py` | `/decisions`, `/checkpoints`, `/signals` |
| `routes/admin.py` | `/ui/*` admin CRUD |
| `demo/mocks.py` | `/mock/*` stub endpoints (hidden from OpenAPI) |
| `ui/` | Vue 3 admin SPA (built to `ui/dist/`, served at `/admin/`) |

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
| `.env.local` | `DB_PASSWORD`, `POSTGRES_PASSWORD`, `SMOKE_ADMIN_TOKEN`, `SMOKE_SAMPLE_TOKEN` |
| `auth.tokens.local.json` | Bearer token map (mounted into the container, not baked into the image) |

The script prints the **admin bearer token once** — paste it into the `/admin/` login prompt. Runtime tokens are not shown and never reach the browser; the admin UI runs test decisions via `POST /ui/test_decisions`.

Re-running `create_demo_env.sh` **preserves an existing `DB_PASSWORD`** but **rotates auth tokens**. Use a fresh admin token after each run.

**If Postgres auth fails** (for example after a first run that generated a new password against an old volume):

```sh
docker compose down -v
bash scripts/create_demo_env.sh
docker compose up -d --build
```

Or use the clean-room helper: `bash scripts/bootstrap_smoke.sh` (destroys the DB volume, generates env if missing, runs API smoke tests only).

Runtime clients **must not** send `tenant_id` or `tenant_name`; attempting to do so returns `403`.

See [docs/API.md](docs/API.md) for token JSON shape.

---

## Admin UI and `/ui` API

The admin console is a **Vue 3 + TypeScript + Vite** SPA with **Pinia** stores and **Vue Router**. Source: [`ui/`](ui/). Architecture: [`docs/UI_REDESIGN.md`](docs/UI_REDESIGN.md). Operator workflows: [`docs/UI_WORKFLOWS.md`](docs/UI_WORKFLOWS.md). Frontend developer guide: [`ui/README.md`](ui/README.md).

| Item | Detail |
|------|--------|
| URL | `http://localhost:8000/admin/` |
| Build output | `ui/dist/` (built in Docker multi-stage image, or `cd ui && npm ci && npm run build` locally) |
| Auth in browser | Admin bearer token in `sessionStorage` (`decisionEngineAdminToken`); not persisted server-side |
| Admin JSON API | `/ui/*` (CRUD, search, test decisions) |
| Active tenant | Selected in the UI; stored in the URL as `?tenant=<uuid>`; sidebar and in-app links preserve the query |
| Tenant-scoped reads | List/search calls pass `tenant_id`; the browser does not receive cross-tenant config rows |
| Dev vs prod UI | `npm run dev` shows a development banner and local token hints; production `npm run build` omits that chrome (`SHOW_DEV_DEMO_UI`) |

`main.py` mounts `ui/dist/` at `/admin/`. Extensionless paths (e.g. `/admin/checkpoints`) fall back to `index.html` for client-side routing. Missing static assets (`.js`, `.css`, etc.) return `404`, not the SPA shell.

---

## Database

PostgreSQL (`risk_engine_db` in Docker Compose). Schema: [`sql/01_schema.sql`](sql/01_schema.sql). Sample data: [`sql/02_sample_data.sql`](sql/02_sample_data.sql). Stable fixture IDs and section map: [`sql/README.md`](sql/README.md).

---

## Quick Start (Docker)

```sh
git clone <your-repo-url>
cd decision-engine
bash scripts/create_demo_env.sh   # required before first boot
docker compose up -d --build
open http://localhost:8000/admin/ # paste admin token from script output
bash scripts/smoke_test.sh
bash scripts/ui_smoke.sh          # requires Node.js; uses SMOKE_ADMIN_TOKEN from .env.local
```

Compose binds the app to **`127.0.0.1:8000`** and Postgres to **`127.0.0.1:5432`** (local demo only).

Clean-room bootstrap (destroys DB volume, generates env if missing, API smoke only):

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

---

## Verification

CI (`.github/workflows/ci.yml`) runs the same gates on push/PR:

```sh
# Frontend (no running stack required)
cd ui && npm ci && npm audit --audit-level=high --omit=optional \
  && npm run typecheck && npm run lint && npm run test:unit && npm run build
(cd scripts && npm ci --no-fund --no-audit && npm audit --audit-level=high --omit=optional)

# Backend + integration (stack required)
bash scripts/create_demo_env.sh    # skip if .env.local exists
docker compose up -d --build
docker compose exec -T -e RUN_INTEGRATION_TESTS=1 risk-engine pytest -q
bash scripts/smoke_test.sh
bash scripts/ui_smoke.sh

# Playwright e2e (stack required; scrubbed env — same pattern as CI)
source scripts/lib/read_env_var.sh
ADMIN_TOKEN="$(read_env_var SMOKE_ADMIN_TOKEN .env.local)"
cd ui
env -i PATH="${PATH}" HOME="${HOME:-}" npx playwright install chromium
env -i PATH="${PATH}" HOME="${HOME:-}" \
  BASE_URL="http://127.0.0.1:8000" \
  SMOKE_ADMIN_TOKEN="${ADMIN_TOKEN}" \
  ./node_modules/.bin/playwright test
```

`ui_smoke.sh` exercises DOM workflows via `scripts/ui_browser_smoke.mjs`. Playwright e2e (`ui/src/tests/e2e/`) covers auth bootstrap, deep links, tenant switching, workflow lifecycle, and SPA static-file handling.

---

## Local Development (without Docker)

1. Start PostgreSQL and create `risk_engine_db`.
2. Apply `sql/01_schema.sql`, then `sql/02_sample_data.sql`.
3. `bash scripts/create_demo_env.sh` and `set -a && source .env.local && set +a`
4. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
5. `cd ui && npm ci && npm run build` — required; `main.py` refuses to start without `ui/dist/`
6. `uvicorn main:app --host 0.0.0.0 --port 8000`

For UI-only work: `cd ui && npm run dev` (Vite on its own port; API must still run on `:8000` for `/ui/*` calls).

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

See [docs/ROADMAP.md](docs/ROADMAP.md).

---

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## License

MIT — see [LICENSE](LICENSE).
