#!/bin/bash
# Read a single KEY=value from an env file without exporting the whole file.
# Usage: VAL="$(read_env_var SMOKE_ADMIN_TOKEN /path/to/.env.local)"
read_env_var() {
  local key="$1"
  local file="$2"
  if [[ ! -f "${file}" ]]; then
    return 1
  fi
  local line
  line="$(grep -E "^${key}=" "${file}" | head -1 || true)"
  if [[ -z "${line}" ]]; then
    return 1
  fi
  local value="${line#*=}"
  value="${value%$'\r'}"
  if [[ "${value}" =~ ^\".*\"$ ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "${value}" =~ ^\'.*\'$ ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "${value}"
}
