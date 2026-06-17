#!/usr/bin/env bash
# End-to-end proof for API cleanup + dev purge against a running stack.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

# shellcheck source=lib/read_env_var.sh
source "${ROOT_DIR}/scripts/lib/read_env_var.sh"

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
ADMIN_TOKEN="$(read_env_var SMOKE_ADMIN_TOKEN .env.local || true)"
PURGE_CONFIRM="$(read_env_var DECISION_ENGINE_DEV_PURGE_CONFIRM .env.local || true)"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "SMOKE_ADMIN_TOKEN required in .env.local" >&2
  exit 1
fi

echo "-> Dev purge status (expect 200 when enabled + configured)"
status_code="$(curl -s -o /tmp/dev-purge-status.json -w "%{http_code}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "${BASE_URL}/ui/dev/purge/status")"
echo "   HTTP ${status_code}"
if [[ "${status_code}" == "200" ]]; then
  [[ -n "${PURGE_CONFIRM}" ]] || { echo "DECISION_ENGINE_DEV_PURGE_CONFIRM missing locally" >&2; exit 1; }
elif [[ "${status_code}" == "404" ]]; then
  echo "   Dev purge disabled (acceptable for prod-like env)"
elif [[ "${status_code}" == "500" ]]; then
  echo "   Dev purge misconfigured on server (missing confirm token)" >&2
  cat /tmp/dev-purge-status.json >&2
  exit 1
else
  echo "Unexpected dev purge status: ${status_code}" >&2
  cat /tmp/dev-purge-status.json >&2
  exit 1
fi

echo "-> Cleanup dry-run"
python3 scripts/cleanup_demo_config_via_api.py --dry-run --token "${ADMIN_TOKEN}" --base-url "${BASE_URL}"

echo "Cleanup integration checks passed."
