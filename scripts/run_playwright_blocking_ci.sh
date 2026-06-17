#!/usr/bin/env bash
# Blocking Playwright behavioral e2e — same env as CI main gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

bash scripts/seed_visual_fixture.sh

cd ui
npm run build
cd "${ROOT}"

docker compose build risk-engine
docker compose up -d risk-engine
sleep 5

cd ui
env -i PATH="${PATH}" HOME="${HOME:-}" npx playwright install chromium
# shellcheck source=scripts/lib/read_env_var.sh
source ../scripts/lib/read_env_var.sh
ADMIN_TOKEN="$(read_env_var SMOKE_ADMIN_TOKEN ../.env.local)"
export CI="${CI:-true}"
export BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
export SMOKE_ADMIN_TOKEN="${ADMIN_TOKEN}"

BLOCKING_SPECS=(
  src/tests/e2e/auth-and-tenant.spec.ts
  src/tests/e2e/workflow-lifecycle.spec.ts
  src/tests/e2e/lifecycle-actions.spec.ts
)

exec env -i PATH="${PATH}" HOME="${HOME:-}" \
  CI="${CI}" \
  BASE_URL="${BASE_URL}" \
  SMOKE_ADMIN_TOKEN="${SMOKE_ADMIN_TOKEN}" \
  ./node_modules/.bin/playwright test "${BLOCKING_SPECS[@]}" "$@"
