#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/destroy.sh"
"${SCRIPT_DIR}/run.sh"
"${SCRIPT_DIR}/smoke_test.sh"
