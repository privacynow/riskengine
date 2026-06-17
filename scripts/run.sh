#!/bin/bash
set -euo pipefail

docker compose up -d --build

echo "Waiting for Postgres..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker compose exec -T postgres psql -U postgres -d risk_engine_db -v ON_ERROR_STOP=1 \
  -f /docker-entrypoint-initdb.d/01_schema.sql
docker compose exec -T postgres psql -U postgres -d risk_engine_db -v ON_ERROR_STOP=1 \
  -f /docker-entrypoint-initdb.d/02_sample_data.sql
