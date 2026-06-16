#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

ENV_FILE="${ROOT_DIR}/.env.local"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_TOKEN="${SMOKE_ADMIN_TOKEN:-}"

echo "UI smoke test against ${BASE_URL}"

echo "-> Static shell and assets (served from Docker-built ui/dist)"
admin_body="$(curl -sf "${BASE_URL}/admin/")"
[[ "${admin_body}" == *"Decision Engine Admin"* ]]
[[ "${admin_body}" == *"/admin/assets/"* ]] || [[ "${admin_body}" == *"assets/index-"* ]]

for asset_path in \
  "assets/favicon.svg" \
  "index.html"; do
  status="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/${asset_path}")"
  [[ "${status}" == "200" ]] || { echo "Missing asset: ${asset_path} (${status})" >&2; exit 1; }
done

if [[ -n "${ADMIN_TOKEN}" ]]; then
  echo "-> GET /ui/tenants with admin token"
  curl -sf "${BASE_URL}/ui/tenants?page=1&size=1" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" >/dev/null

  echo "-> POST /ui/test_decisions with admin token"
  curl -sf -X POST "${BASE_URL}/ui/test_decisions" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"tenant_id":"11111111-1111-1111-1111-111111111111","checkpoint_name":"Onboarding","correlation_id":"UI_SMOKE_TEST"}' >/dev/null
else
  echo "-> Skipping authenticated API checks (SMOKE_ADMIN_TOKEN not set)" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required for browser UI smoke" >&2
  exit 1
fi

echo "-> Browser UI smoke (Playwright)"
export BASE_URL SMOKE_ADMIN_TOKEN="${ADMIN_TOKEN}"
if [[ ! -d "${SCRIPT_DIR}/node_modules/playwright" ]]; then
  echo "   Installing Playwright dependencies (first run)…"
  (cd "${SCRIPT_DIR}" && npm ci --no-fund --no-audit)
fi
(cd "${SCRIPT_DIR}" && npx playwright install chromium)
(cd "${SCRIPT_DIR}" && node ui_browser_smoke.mjs)

echo "UI smoke test passed."
