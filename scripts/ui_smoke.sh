#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

# shellcheck source=lib/read_env_var.sh
source "${SCRIPT_DIR}/lib/read_env_var.sh"

ENV_FILE="${ROOT_DIR}/.env.local"
BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_TOKEN="${SMOKE_ADMIN_TOKEN:-}"

if [[ -z "${ADMIN_TOKEN}" && -f "${ENV_FILE}" ]]; then
  ADMIN_TOKEN="$(read_env_var SMOKE_ADMIN_TOKEN "${ENV_FILE}" || true)"
fi

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
# Install tooling without inheriting app/admin secrets in the environment.
if [[ ! -d "${SCRIPT_DIR}/node_modules/playwright" ]]; then
  echo "   Installing Playwright dependencies (first run)…"
  (cd "${SCRIPT_DIR}" && env -i PATH="${PATH}" HOME="${HOME:-}" npm ci --no-fund --no-audit)
fi
(cd "${SCRIPT_DIR}" && env -i PATH="${PATH}" HOME="${HOME:-}" npx playwright install chromium)
(
  cd "${SCRIPT_DIR}"
  env -i PATH="${PATH}" HOME="${HOME:-}" \
    BASE_URL="${BASE_URL}" \
    SMOKE_ADMIN_TOKEN="${ADMIN_TOKEN}" \
    node ui_browser_smoke.mjs
)

echo "UI smoke test passed."
