# Deployment

This repository is designed to run locally or on any host with Docker Compose. There are **no project-specific production deploy scripts** in `scripts/`; use the patterns below.

## Recommended: Docker Compose

On a VM or bare-metal host with Docker installed:

```sh
bash scripts/create_demo_env.sh
docker compose up -d --build
bash scripts/smoke_test.sh
bash scripts/ui_smoke.sh    # optional; requires Node.js and SMOKE_ADMIN_TOKEN in .env.local
```

The `docker compose build` step compiles the admin UI (`ui/dist/`) in a Node build stage and copies it into the Python image. No Node.js is required on the host for a normal deploy.

Expose port `8000` through your reverse proxy or security group. Do **not** publish the admin UI or APIs to the public internet without authentication and the hardening described in [ARCHITECTURE.md](ARCHITECTURE.md) and the README production readiness section.

`create_demo_env.sh` writes ignored `.env.local` and `auth.tokens.local.json`. Docker Compose loads them automatically.

## Environment variables

### Auth (required)

| Variable | Purpose |
|----------|---------|
| `DECISION_ENGINE_AUTH_TOKENS` | JSON map of bearer token → `{ tenant_id, actor_id, roles }` |
| `DECISION_ENGINE_AUTH_TOKENS_FILE` | Path to the same JSON structure |

The app fails startup if neither is set.

### Database (required)

| Variable | Notes |
|----------|--------|
| `DB_HOST` | `postgres` in Compose |
| `DB_PORT` | `5432` |
| `DB_NAME` | `risk_engine_db` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | **Required** — generated into `.env.local`; no default in app code |
| `POSTGRES_PASSWORD` | Must match `DB_PASSWORD` for the Postgres container |

Postgres binds to **`127.0.0.1:5432`** only. The app binds to **`127.0.0.1:8000`**. Override via Compose for non-demo environments.

If Postgres authentication fails after regenerating `.env.local`, reset the volume before restarting:

```sh
docker compose down -v
bash scripts/create_demo_env.sh
docker compose up -d --build
```

## Optional: sync artifacts to a remote host

If you deploy without git on the target host, copy the repo (or image) with your own tooling. Example pattern using environment variables — **do not commit hostnames or key paths**:

```sh
export DEPLOY_HOST=your.host.example
export DEPLOY_KEY=/path/to/key.pem
export DEPLOY_USER=ec2-user
export REMOTE_DIR=decision-engine

scp -i "$DEPLOY_KEY" -r . "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/"
ssh -i "$DEPLOY_KEY" "${DEPLOY_USER}@${DEPLOY_HOST}" "cd ${REMOTE_DIR} && docker compose up -d --build"
```

Private one-off scp helpers, if you use them, belong outside this repo (for example under ignored `docs/internal/`).

## Database initialization

First boot of the Postgres container runs, in order:

1. `sql/01_schema.sql`
2. `sql/02_sample_data.sql`

To reset completely:

```sh
bash scripts/destroy.sh
bash scripts/run.sh
bash scripts/smoke_test.sh
```

## Admin UI at runtime

- Served from `ui/dist/` inside the container at `/admin/`.
- If `ui/dist/` is missing at startup, `engine.main` raises `RuntimeError` with build instructions.
- To rebuild the UI without changing Python code: `cd ui && npm ci && npm run build`, then rebuild the image or copy `dist/` into the running layout before restart.
