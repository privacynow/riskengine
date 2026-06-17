#!/usr/bin/env bash
set -euo pipefail

umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-${ROOT_DIR}/.env.local}"
TOKENS_FILE="${2:-${ROOT_DIR}/auth.tokens.local.json}"

python3 - <<'PY' "${ENV_FILE}" "${TOKENS_FILE}"
import json
import os
import secrets
import sys
from pathlib import Path

env_file = Path(sys.argv[1])
tokens_file = Path(sys.argv[2])
sample_tenant = "11111111-1111-1111-1111-111111111111"
other_tenant = "99999999-9999-9999-9999-999999999999"

sample_token = secrets.token_hex(24)
other_token = secrets.token_hex(24)
admin_token = secrets.token_hex(24)
dev_purge_confirm = secrets.token_hex(16)
from cryptography.fernet import Fernet

encryption_key = Fernet.generate_key().decode("utf-8")

existing_db_password = None
if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("DB_PASSWORD="):
            value = line.split("=", 1)[1].strip()
            if value:
                existing_db_password = value
            break

db_password = existing_db_password or secrets.token_urlsafe(24)

tokens = {
    sample_token: {
        "tenant_id": sample_tenant,
        "actor_id": "sample-lending-client",
        "roles": ["runtime"],
    },
    other_token: {
        "tenant_id": other_tenant,
        "actor_id": "other-bank-client",
        "roles": ["runtime"],
    },
    admin_token: {
        "tenant_id": None,
        "actor_id": "admin-local",
        "roles": ["admin"],
    },
}

tokens_file.write_text(json.dumps(tokens, indent=2) + "\n", encoding="utf-8")
os.chmod(tokens_file, 0o600)

lines = [
    "# Generated local demo credentials — do not commit this file.",
    "DECISION_ENGINE_AUTH_TOKENS_FILE=./auth.tokens.local.json",
    f"SMOKE_SAMPLE_TOKEN={sample_token}",
    f"SMOKE_OTHER_TOKEN={other_token}",
    f"SMOKE_ADMIN_TOKEN={admin_token}",
    f"DB_PASSWORD={db_password}",
    f"POSTGRES_PASSWORD={db_password}",
    "DECISION_ENGINE_DEV_PURGE=1",
    f"DECISION_ENGINE_DEV_PURGE_CONFIRM={dev_purge_confirm}",
    f"DECISION_ENGINE_SECRET_ENCRYPTION_KEY={encryption_key}",
    "",
]
env_file.write_text("\n".join(lines), encoding="utf-8")
os.chmod(env_file, 0o600)

print(f"Wrote {env_file}")
print(f"Wrote {tokens_file}")
print(f"Admin bearer token: {admin_token}")
print(f"Dev purge confirm header (X-Dev-Purge-Confirm): {dev_purge_confirm}")
print("Dev purge body confirmPhrase:")
print("  I understand this permanently deletes dev audit data for the tenant")
if not existing_db_password:
    print("Generated new DB_PASSWORD. If Postgres auth fails, reset the volume:")
    print("  docker compose down -v && docker compose up -d --build")
PY
