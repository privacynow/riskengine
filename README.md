# Decision Engine

Decision Engine helps teams define, run, test, and audit automated business decisions across tenants. It is built for policies that depend on reusable data signals, versioned rules, governed promotion, and traceable outcomes.

## What It Does

- Models business decisions as lifecycle checkpoints with linked signals and rule expressions.
- Reuses signals across decisions: integrations, variables, expression-derived values, and local functions.
- Runs decisions with tenant isolation, cost controls, timeouts, and durable audit logs.
- Lets operators preflight DSL, test drafts, promote versions with a reason, inspect decision traces, and review signal failures.
- Audits promotion, deactivation, and reactivation; deleting a current checkpoint or signal version returns `409`.

## Quick Start

Prerequisites: Docker and Docker Compose.

```sh
bash scripts/create_demo_env.sh
docker compose up -d --build
```

`create_demo_env.sh` writes ignored local files:

- `.env.local` — database password and smoke-test tokens
- `auth.tokens.local.json` — bearer-token map mounted into the container

The script prints the admin bearer token once. Paste that token into the admin login at `/admin/`.

Then visit `http://localhost:8000/admin/`.

Run smoke checks:

```sh
bash scripts/smoke_test.sh
bash scripts/ui_smoke.sh
```

`ui_smoke.sh` requires Node.js on the host for the browser check. Normal Docker startup does not; the admin UI is built inside the Docker image.

## Runtime Example

A runtime request evaluates a named lifecycle checkpoint under the tenant bound to the bearer token. Do not send `tenant_id` or `tenant_name` in runtime requests.

```sh
source scripts/lib/read_env_var.sh
SAMPLE_TOKEN="$(read_env_var SMOKE_SAMPLE_TOKEN .env.local)"

curl -s -X POST http://localhost:8000/decisions \
  -H "Authorization: Bearer ${SAMPLE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_name":"Onboarding","applicant_id":"demo-1","correlation_id":"demo"}'
```

## URLs

| URL | Purpose |
|-----|---------|
| `http://localhost:8000/admin/` | Admin workbench |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/openapi.json` | OpenAPI JSON |

Docker Compose binds the app to `127.0.0.1:8000` and Postgres to `127.0.0.1:5432`.

## Common Commands

```sh
docker compose ps
docker compose logs -f risk-engine
docker compose down
docker compose down -v          # reset database volume
bash scripts/redeploy_all.sh    # reset volume, rebuild, wait for API, smoke test
bash scripts/test_seed_idempotency.sh
```

## Reset Demo Data

Use a full volume reset when you want a clean local environment with the curated demo tenants, checkpoints, signals, associations, and audit sample:

```sh
bash scripts/create_demo_env.sh
docker compose down -v
docker compose up -d --build
bash scripts/smoke_test.sh
```

This is the most reliable path because it recreates Postgres, reapplies schema and seed SQL, and exercises smoke checks. Seed SQL is also designed to re-apply cleanly against an existing volume; verify that path with:

```sh
bash scripts/test_seed_idempotency.sh
```

For visual regression data, seed the separate fixture after the stack is running:

```sh
bash scripts/seed_visual_fixture.sh
```

To remove only scratch/test tenants from a running database, use the API cleanup script instead:

```sh
python3 scripts/cleanup_demo_config_via_api.py --dry-run
python3 scripts/cleanup_demo_config_via_api.py --yes
```

If Postgres authentication fails after regenerating `.env.local`, reset the volume:

```sh
docker compose down -v
bash scripts/create_demo_env.sh
docker compose up -d --build
```

## Repository Layout

| Path | Purpose |
|------|---------|
| `engine/` | Application service, auth, routes, decision orchestration |
| `ui/` | Admin workbench, built to `ui/dist/` |
| `sql/` | Postgres schema and sample seed data |
| `scripts/` | Bootstrap, Docker, smoke, and UI test helpers |
| `tests/` | Pytest integration and contract tests |
| `docs/` | API, architecture, deployment, DSL, development notes |

## Documentation

| Document | Use it for |
|----------|------------|
| [API](docs/API.md) | Auth shape, runtime/admin API notes, OpenAPI source of truth |
| [Architecture](docs/ARCHITECTURE.md) | Tenancy, versioning, DSL, orchestration, admin write model |
| [Deployment](docs/DEPLOYMENT.md) | Docker deployment, environment variables, database initialization |
| [Development](docs/DEVELOPMENT.md) | Local development, full test matrix, Playwright workflow |
| [DSL guide](docs/DSL_GUIDE.md) | Authoring checkpoint DSL and expression signals |
| [Admin UI](ui/README.md) | Admin workbench implementation and UI test details |

## Security Notes

No bearer token values are committed in source, seed data, or Docker images. Local demo credentials are generated into ignored files.

Do not expose this stack to the public internet without production identity, TLS, secret management, and an egress policy for outbound signal calls. See [Deployment](docs/DEPLOYMENT.md) and [Architecture](docs/ARCHITECTURE.md).

## License

MIT — see [LICENSE](LICENSE).
