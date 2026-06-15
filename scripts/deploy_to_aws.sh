#!/bin/bash
set -euo pipefail

: "${DEPLOY_HOST:?Set DEPLOY_HOST to the target host}"
: "${DEPLOY_KEY:?Set DEPLOY_KEY to the SSH private key path}"
DEPLOY_USER="${DEPLOY_USER:-ec2-user}"
REMOTE_DIR="${REMOTE_DIR:-decision-engine}"

scp -i "$DEPLOY_KEY" ui/app.js ui/index.html "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/ui/"
scp -i "$DEPLOY_KEY" sql/02_sample_data.sql sql/01_schema.sql "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/sql/"
scp -i "$DEPLOY_KEY" scripts/*.sh "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/scripts/"
scp -i "$DEPLOY_KEY" main.py Dockerfile docker-compose.yml requirements.txt LICENSE "${DEPLOY_USER}@${DEPLOY_HOST}:/home/${DEPLOY_USER}/${REMOTE_DIR}/"
