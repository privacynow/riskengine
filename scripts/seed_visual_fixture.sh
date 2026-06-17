#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL_FILE="${ROOT}/tests/fixtures/visual_fixture.sql"

if [[ ! -f "${SQL_FILE}" ]]; then
  echo "Missing ${SQL_FILE}" >&2
  exit 1
fi

docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres \
  psql -U postgres -d risk_engine_db -v ON_ERROR_STOP=1 < "${SQL_FILE}"

LIFECYCLE_SQL="${ROOT}/tests/fixtures/lifecycle_e2e_fixture.sql"
docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres \
  psql -U postgres -d risk_engine_db -v ON_ERROR_STOP=1 < "${LIFECYCLE_SQL}"

echo "Visual and lifecycle e2e fixtures seeded."
