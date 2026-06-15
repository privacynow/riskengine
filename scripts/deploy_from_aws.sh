#!/bin/bash
set -euo pipefail

: "${DEPLOY_HOST:?Set DEPLOY_HOST to the target host}"
: "${DEPLOY_KEY:?Set DEPLOY_KEY to the SSH private key path}"
DEPLOY_USER="${DEPLOY_USER:-ec2-user}"
REMOTE_DIR="${REMOTE_DIR:-decision-engine}"

scp -i "$DEPLOY_KEY" "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/ui/"* ui/
scp -i "$DEPLOY_KEY" "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/sql/"* sql/
scp -i "$DEPLOY_KEY" "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/scripts/"*.sh scripts/
scp -i "$DEPLOY_KEY" "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/Dockerfile" .
scp -i "$DEPLOY_KEY" "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/docker-compose.yml" .
scp -i "$DEPLOY_KEY" "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/main.py" .
scp -i "$DEPLOY_KEY" "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/requirements.txt" .
