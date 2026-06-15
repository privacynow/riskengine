#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

docker compose stop risk-engine postgres || true
docker compose rm -f postgres || true
docker volume rm decision-engine_postgres_data 2>/dev/null || true

docker compose up -d postgres

echo "Waiting for Postgres init..."
for i in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
    if docker compose exec -T postgres psql -U postgres -d risk_engine_db -c "SELECT 1 FROM tenants LIMIT 1;" >/dev/null 2>&1; then
      break
    fi
  fi
  sleep 2
  if [ "$i" -eq 60 ]; then
    echo "Timed out waiting for Postgres seed data" >&2
    docker compose logs postgres
    exit 1
  fi
done

docker compose up -d --build risk-engine
