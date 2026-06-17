#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

ENV_FILE="${ROOT_DIR}/.env.local"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Run: bash scripts/create_demo_env.sh" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

: "${SMOKE_SAMPLE_TOKEN:?SMOKE_SAMPLE_TOKEN missing from .env.local}"
: "${SMOKE_OTHER_TOKEN:?SMOKE_OTHER_TOKEN missing from .env.local}"
: "${SMOKE_ADMIN_TOKEN:?SMOKE_ADMIN_TOKEN missing from .env.local}"

BASE_URL="${BASE_URL:-http://localhost:8000}"
SAMPLE_TOKEN="${SMOKE_SAMPLE_TOKEN}"
OTHER_TOKEN="${SMOKE_OTHER_TOKEN}"
ADMIN_TOKEN="${SMOKE_ADMIN_TOKEN}"

auth_hdr() { echo "Authorization: Bearer $1"; }

echo "Smoke test against ${BASE_URL}"

echo "-> GET /checkpoints/Onboarding without auth returns 401"
status="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/checkpoints/Onboarding")"
[[ "${status}" == "401" ]]

echo "-> GET /checkpoints/Onboarding with runtime token (auth-derived tenant)"
checkpoint_body="$(curl -sf "${BASE_URL}/checkpoints/Onboarding" \
  -H "$(auth_hdr "${SAMPLE_TOKEN}")")"
[[ "${checkpoint_body}" == *"Onboarding"* ]]

echo "-> GET /checkpoints/Onboarding?tenant_name=OTHER BANK with sample token returns 403"
status="$(curl -s -o /dev/null -w "%{http_code}" \
  "${BASE_URL}/checkpoints/Onboarding?tenant_name=OTHER%20BANK" \
  -H "$(auth_hdr "${SAMPLE_TOKEN}")")"
[[ "${status}" == "403" ]]

echo "-> GET /admin/"
admin_body="$(curl -sf "${BASE_URL}/admin/")"
[[ "${admin_body}" == *"Decision Engine Admin"* ]]
[[ "${admin_body}" == *"assets/index-"* ]]

echo "-> POST /decisions without auth returns 401"
status="$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/decisions" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_name":"Onboarding","applicant_id":"smoke-applicant","correlation_id":"SMOKE_TEST"}')"
[[ "${status}" == "401" ]]

echo "-> POST /decisions with tenant_name in body returns 403"
status="$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/decisions" \
  -H "$(auth_hdr "${SAMPLE_TOKEN}")" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_name":"Onboarding","tenant_name":"SAMPLE LENDING","applicant_id":"smoke-applicant","correlation_id":"SMOKE_TEST"}')"
[[ "${status}" == "403" ]]

echo "-> POST /decisions (SAMPLE LENDING token / Onboarding)"
response="$(curl -sf -X POST "${BASE_URL}/decisions" \
  -H "$(auth_hdr "${SAMPLE_TOKEN}")" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_name":"Onboarding","applicant_id":"smoke-applicant","correlation_id":"SMOKE_TEST"}')"

[[ "${response}" == *'"decision_id"'* ]]
[[ "${response}" == *'"decision_outcome":"APPROVE"'* ]]
[[ "${response}" != *"inactive_demo"* ]]

echo "-> POST /decisions (OTHER BANK token — same checkpoint name, different tenant)"
response_other="$(curl -sf -X POST "${BASE_URL}/decisions" \
  -H "$(auth_hdr "${OTHER_TOKEN}")" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_name":"Onboarding","applicant_id":"smoke-applicant","correlation_id":"SMOKE_TEST_OTHER"}')"

[[ "${response_other}" == *'"decision_id"'* ]]
[[ "${response_other}" == *'"decision_outcome":"DECLINE"'* ]]

echo "-> GET /ui/tenants without auth returns 401"
status="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/ui/tenants?page=1&size=1")"
[[ "${status}" == "401" ]]

echo "-> GET /ui/tenants with admin token succeeds"
curl -sf "${BASE_URL}/ui/tenants?page=1&size=1" -H "$(auth_hdr "${ADMIN_TOKEN}")" >/dev/null

echo "-> POST /ui/test_decisions with admin token succeeds"
curl -sf -X POST "${BASE_URL}/ui/test_decisions" \
  -H "$(auth_hdr "${ADMIN_TOKEN}")" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"11111111-1111-1111-1111-111111111111","checkpoint_name":"Onboarding","correlation_id":"SMOKE_ADMIN_TEST"}' >/dev/null

echo "Smoke test passed."
