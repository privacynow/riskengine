#!/usr/bin/env bash
# Non-blocking visual snapshot review — uploads artifacts for human review.
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
  ./node_modules/.bin/playwright test src/tests/e2e/visual-review.spec.ts "$@"
