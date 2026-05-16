#!/usr/bin/env bash

set -Eeuo pipefail

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 2
  fi
}

quote() {
  printf "%q" "$1"
}

require_env DEPLOY_HOST

DEPLOY_USER="${DEPLOY_USER:-root}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/repaircrm/crm}"
DEPLOY_COMPOSE_PROJECT="${DEPLOY_COMPOSE_PROJECT:-repaircrm}"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.production}"
DEPLOY_DOMAIN="${DEPLOY_DOMAIN:-b00bs.ru}"
DEPLOY_SSH_PORT="${DEPLOY_SSH_PORT:-22}"
DEPLOY_SSH_KEY_PATH="${DEPLOY_SSH_KEY_PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${DEPLOY_USER}@${DEPLOY_HOST}"

SSH_CMD=(ssh -p "$DEPLOY_SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)
if [[ -n "$DEPLOY_SSH_KEY_PATH" ]]; then
  SSH_CMD+=(-i "$DEPLOY_SSH_KEY_PATH")
fi

RSYNC_SSH="${SSH_CMD[*]}"

echo "Deploying RepairCRM to ${REMOTE}:${DEPLOY_PATH}"

"${SSH_CMD[@]}" "$REMOTE" "mkdir -p $(quote "$DEPLOY_PATH")"

rsync -az --delete \
  -e "$RSYNC_SSH" \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  --exclude 'a.txt' \
  --exclude '.env.production' \
  --exclude 'node_modules/' \
  --exclude 'frontend/crm-app/.angular/' \
  --exclude 'frontend/crm-app/node_modules/' \
  --exclude 'frontend/crm-app/dist/' \
  --exclude '.tmp-screens/' \
  --exclude 'logs/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.mypy_cache/' \
  "${ROOT_DIR}/" "${REMOTE}:${DEPLOY_PATH}/"

REMOTE_ENV=(
  "DEPLOY_PATH=$(quote "$DEPLOY_PATH")"
  "DEPLOY_ENV_FILE=$(quote "$DEPLOY_ENV_FILE")"
  "DEPLOY_COMPOSE_PROJECT=$(quote "$DEPLOY_COMPOSE_PROJECT")"
  "DEPLOY_DOMAIN=$(quote "$DEPLOY_DOMAIN")"
)

"${SSH_CMD[@]}" "$REMOTE" "${REMOTE_ENV[*]} bash -s" <<'REMOTE_SCRIPT'
set -Eeuo pipefail

cd "$DEPLOY_PATH"
test -f "$DEPLOY_ENV_FILE"

docker compose -p "$DEPLOY_COMPOSE_PROJECT" --env-file "$DEPLOY_ENV_FILE" config -q
docker compose -p "$DEPLOY_COMPOSE_PROJECT" --env-file "$DEPLOY_ENV_FILE" up -d --build --remove-orphans
docker compose -p "$DEPLOY_COMPOSE_PROJECT" --env-file "$DEPLOY_ENV_FILE" ps

docker compose -p "$DEPLOY_COMPOSE_PROJECT" --env-file "$DEPLOY_ENV_FILE" exec -T backend \
  python manage.py check

health_status="$(curl -sS \
  -o /tmp/repaircrm-health-response \
  -w '%{http_code}' \
  -H "Host: ${DEPLOY_DOMAIN}" \
  -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8080/api/health)"

if [ "$health_status" != "200" ]; then
  echo "Healthcheck failed with HTTP ${health_status}" >&2
  cat /tmp/repaircrm-health-response >&2 || true
  exit 1
fi
REMOTE_SCRIPT

echo "Deploy completed"
