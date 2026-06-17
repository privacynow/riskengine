#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if ! docker compose exec -T postgres pg_isready -U postgres -d risk_engine_db >/dev/null 2>&1; then
  echo "Postgres is not running. Start the stack first (e.g. bash scripts/run.sh)." >&2
  exit 1
fi

apply_seed() {
  local label="$1"
  echo "-> Applying seed SQL (${label})"
  docker compose exec -T postgres psql -U postgres -d risk_engine_db -v ON_ERROR_STOP=1 \
    -f /docker-entrypoint-initdb.d/02_sample_data.sql
}

apply_seed "first pass"
apply_seed "second pass (idempotency)"

echo "Seed idempotency check passed."
