#!/bin/bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "Smoke test against ${BASE_URL}"

echo "-> GET /checkpoints/Onboarding"
checkpoint_body="$(curl -sf "${BASE_URL}/checkpoints/Onboarding")"
[[ "${checkpoint_body}" == *"Onboarding"* ]]

echo "-> GET /admin/"
admin_body="$(curl -sf "${BASE_URL}/admin/")"
[[ "${admin_body}" == *"Risk Decision Engine Admin"* ]]

echo "-> POST /decisions (Onboarding)"
response="$(curl -sf -X POST "${BASE_URL}/decisions" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_name":"Onboarding","applicant_id":"smoke-applicant","correlation_id":"SMOKE_TEST"}')"

[[ "${response}" == *'"decision_id"'* ]]
[[ "${response}" == *'"final_decision_value":"True"'* ]]

echo "Smoke test passed."
