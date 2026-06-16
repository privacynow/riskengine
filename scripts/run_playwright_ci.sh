#!/usr/bin/env bash
# Run Playwright the same way GitHub Actions does (after services are up).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

bash scripts/seed_visual_fixture.sh

cd ui
env -i PATH="${PATH}" HOME="${HOME:-}" npx playwright install chromium
# shellcheck source=scripts/lib/read_env_var.sh
source ../scripts/lib/read_env_var.sh
ADMIN_TOKEN="$(read_env_var SMOKE_ADMIN_TOKEN ../.env.local)"
export CI="${CI:-true}"
export BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
export SMOKE_ADMIN_TOKEN="${ADMIN_TOKEN}"

exec env -i PATH="${PATH}" HOME="${HOME:-}" \
  CI="${CI}" \
  BASE_URL="${BASE_URL}" \
  SMOKE_ADMIN_TOKEN="${SMOKE_ADMIN_TOKEN}" \
  ./node_modules/.bin/playwright test "$@"
