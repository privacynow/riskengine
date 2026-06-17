#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

"${ROOT_DIR}/scripts/destroy.sh"
"${ROOT_DIR}/scripts/run.sh"

echo "Waiting for API..."
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:8000/admin/" >/dev/null 2>&1; then
    break
  fi
  sleep 1
  if [ "$i" -eq 30 ]; then
    echo "Timed out waiting for API" >&2
    exit 1
  fi
done

"${ROOT_DIR}/scripts/smoke_test.sh"
