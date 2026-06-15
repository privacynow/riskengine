#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

docker compose down -v
docker compose up -d --build

echo "Waiting for services..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/checkpoints/Onboarding >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [ "$i" -eq 60 ]; then
    echo "Timed out waiting for app" >&2
    docker compose logs risk-engine
    exit 1
  fi
done

bash scripts/smoke_test.sh
