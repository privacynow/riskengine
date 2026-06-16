# Development

Commands and workflows for working on the Decision Engine locally.

## Stack

```sh
bash scripts/create_demo_env.sh
docker compose up -d --build
```

The app serves:

- Admin UI: `http://localhost:8000/admin/`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Backend Tests

Run integration tests inside the app container:

```sh
docker compose exec -T -e RUN_INTEGRATION_TESTS=1 risk-engine pytest -q
```

Run the API smoke test:

```sh
bash scripts/smoke_test.sh
```

## Frontend Tests

Frontend source lives in `ui/`.

```sh
cd ui
npm ci
npm run typecheck
npm run lint
npm run test:unit
npm run build
```

Dependency audit gates:

```sh
npm --prefix ui run audit:high
npm --prefix scripts audit --audit-level=high --omit=optional
```

## Browser Tests

The stack must be running before browser tests.

```sh
bash scripts/seed_visual_fixture.sh
source scripts/lib/read_env_var.sh
ADMIN_TOKEN="$(read_env_var SMOKE_ADMIN_TOKEN .env.local)"

cd ui
env -i PATH="${PATH}" HOME="${HOME:-}" npx playwright install chromium
env -i PATH="${PATH}" HOME="${HOME:-}" \
  BASE_URL="http://127.0.0.1:8000" \
  SMOKE_ADMIN_TOKEN="${ADMIN_TOKEN}" \
  ./node_modules/.bin/playwright test
```

Keep install tooling out of the application secret environment. Do not `source .env.local` before `npm ci` or `playwright install`.

The lighter UI smoke wrapper is:

```sh
bash scripts/ui_smoke.sh
```

## Local Python Process

Docker is the normal path. To run the Python app directly:

1. Start PostgreSQL and create `risk_engine_db`.
2. Apply `sql/01_schema.sql`, then `sql/02_sample_data.sql`.
3. Run `bash scripts/create_demo_env.sh`.
4. Export the required environment variables from `.env.local`.
5. Create a virtualenv and install Python dependencies.
6. Build the admin UI: `cd ui && npm ci && npm run build`.
7. Start FastAPI: `uvicorn engine.main:app --host 0.0.0.0 --port 8000`.

`engine.main` requires `ui/dist/` at startup because `/admin/` is served by FastAPI.

## UI Development Server

For UI-only iteration:

```sh
cd ui
npm run dev
```

The Vite dev server proxies `/ui` and `/decisions` to `http://localhost:8000`, so the API stack still needs to be running.

## Resetting State

Use this when you want a clean local environment with the curated demo data from `sql/02_sample_data.sql`:

```sh
bash scripts/create_demo_env.sh
docker compose down -v
docker compose up -d --build
bash scripts/smoke_test.sh
```

`create_demo_env.sh` preserves an existing database password but rotates auth tokens. Use the newly printed admin token after rerunning it.

Postgres init SQL runs only when the database volume is created. If you remove seeded demo tenants from an existing volume, they will not come back until you reset the volume or manually re-apply the seed SQL.

For visual regression tests, seed the deterministic visual tenant after the stack is running:

```sh
bash scripts/seed_visual_fixture.sh
```

If you only need to remove scratch/test tenants and keep the existing volume, use the API cleanup script:

```sh
python3 scripts/cleanup_demo_config_via_api.py --dry-run
python3 scripts/cleanup_demo_config_via_api.py --yes
```

Use `--include-seed-tenants --yes` only when you intend to remove `SAMPLE LENDING`, `OTHER BANK`, or `VISUAL FIXTURE BANK`; a full volume reset is the preferred way to recreate them cleanly.
