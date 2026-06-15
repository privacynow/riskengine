# Deployment

This repository is designed to run locally or on any host with Docker Compose. There are **no project-specific production deploy scripts** in `scripts/`; use the patterns below.

## Recommended: Docker Compose

On a VM or bare-metal host with Docker installed:

```sh
git clone <repo-url> decision-engine
cd decision-engine
docker compose up -d --build
bash scripts/smoke_test.sh
```

Expose port `8000` through your reverse proxy or security group. Do **not** publish the admin UI or APIs to the public internet without authentication (see [ROADMAP.md](../ROADMAP.md)).

## Environment variables

The app container reads standard Postgres settings:

| Variable | Default |
|----------|---------|
| `DB_HOST` | `postgres` (in Compose) |
| `DB_PORT` | `5432` |
| `DB_NAME` | `risk_engine_db` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | `postgres` |

Override these in `docker-compose.yml` or via Compose env files for non-demo environments.

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
