#!/usr/bin/env bash
# CRVS one-host deployment script (FINAL, CLEAN, PROD-SAFE)
#
# Usage:
#   ./deploy/deploy.sh [dev|staging|prod]
#   ./deploy/deploy.sh onehost
#   ./deploy/deploy.sh onehost-dev
#   ./deploy/deploy.sh onehost-prod
#
# PROD SAFETY:
#   docker stop is BLOCKED in onehost-prod
#   To allow it explicitly:
#     CRVS_ALLOW_DOCKER_STOP=1 ./deploy/deploy.sh onehost-prod

set -euo pipefail

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
if [ -f deploy/.env ]; then
  echo "Loading deploy/.env"
  set -a
  source deploy/.env
  set +a
fi

ENVIRONMENT=${1:-${ENVIRONMENT:-dev}}
BASE=docker-compose.base.yml

# --------------------------------------------------
# Helpers
# --------------------------------------------------
wait_for_tcp() {
  local host=$1
  local port=$2
  local label=${3:-"$host:$port"}
  echo "Waiting for TCP ${label}..."
  for i in {1..60}; do
    if (echo >/dev/tcp/${host}/${port}) >/dev/null 2>&1; then
      echo "OK: ${label}"
      return 0
    fi
    sleep 1
  done
  echo "Timeout waiting for ${label}" >&2
  return 1
}

wait_for_http() {
  local url=$1
  local label=${2:-$url}
  echo "Waiting for HTTP ${label}..."
  for i in {1..60}; do
    if curl -fsS -o /dev/null "$url"; then
      echo "OK: ${label}"
      return 0
    fi
    sleep 1
  done
  echo "Timeout waiting for ${label}" >&2
  return 1
}

# --------------------------------------------------
# Adaptive waiters (localhost ↔ domain)
# --------------------------------------------------
wait_for_app() {
  if [[ "${FORCE_LOCALHOST_WAIT:-}" == "true" ]]; then
    wait_for_http "http://localhost" "App (forced localhost)"
    return
  fi

  if [[ "$ENVIRONMENT" == "onehost-prod" ]] && [[ -n "${CRVS_APP_DOMAIN:-}" ]]; then
    wait_for_http "https://${CRVS_APP_DOMAIN}" "App (${CRVS_APP_DOMAIN})"
  else
    wait_for_http "http://localhost" "App (localhost)"
  fi
}

wait_for_jitsi() {
  if [[ "${FORCE_LOCALHOST_WAIT:-}" == "true" ]]; then
    wait_for_tcp localhost 8443 "Jitsi tcp:8443 (forced localhost)"
    return
  fi

  if [[ "$ENVIRONMENT" == "onehost-prod" ]] && [[ -n "${CRVS_JITSI_DOMAIN:-}" ]]; then
    wait_for_http "https://${CRVS_JITSI_DOMAIN}" "Jitsi (${CRVS_JITSI_DOMAIN})"
  else
    wait_for_tcp localhost 8443 "Jitsi tcp:8443"
  fi
}

# --------------------------------------------------
# Safety checks (PROD)
# --------------------------------------------------
if [[ "$ENVIRONMENT" == "onehost-prod" ]]; then
  if [[ -z "${CRVS_APP_DOMAIN:-}" || -z "${CRVS_JITSI_DOMAIN:-}" ]]; then
    echo "❌ ERROR: onehost-prod requires CRVS_APP_DOMAIN and CRVS_JITSI_DOMAIN"
    exit 1
  fi
fi

# --------------------------------------------------
# Run Ansible (once, clean)
# --------------------------------------------------
echo
echo ":::::::::::::::::::::: Running Ansible ::::::::::::::::::::::"
echo

if ! command -v ansible-playbook >/dev/null 2>&1; then
  echo "Installing Ansible..."
  pip3 install ansible
fi

if [ ! -f "../infrastructure/inventory.ini" ]; then
  echo "❌ inventory.ini not found"
  exit 1
fi

cd ../infrastructure
ansible-playbook -i inventory.ini site.yml
cd - >/dev/null

echo "✅ Ansible completed"
echo

# --------------------------------------------------
# generate passwords for jitsi
# --------------------------------------------------
./gen-passwords.sh
# --------------------------------------------------
# Create directories and network for jitsi
# --------------------------------------------------
mkdir -p ~/.jitsi-meet-cfg/{web,transcripts,prosody/config,prosody/prosody-plugins-custom,jicofo,jvb,jigasi,jibri}

docker network create crvslearning

# --------------------------------------------------
# Deployment modes
# --------------------------------------------------
case "$ENVIRONMENT" in
  onehost)
    FILES=(-f "$BASE" -f docker-compose.jitsi.yml -f docker-compose.override.yml)
    ;;
  onehost-dev)
    FILES=(-f "$BASE" -f docker-compose.jitsi.yml -f docker-compose.override.yml -f docker-compose.dev.yml)
    ;;
  onehost-prod)
    FILES=(-f "$BASE" -f docker-compose.jitsi.yml -f docker-compose.override.yml -f docker-compose.prod.yml)
    ;;
  dev)
    FILES=(-f "$BASE" -f docker-compose.dev.yml)
    ;;
  staging)
    FILES=(-f "$BASE" -f docker-compose.staging.yml)
    ;;
  prod)
    FILES=(-f "$BASE" -f docker-compose.prod.yml)
    ;;
  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    exit 1
    ;;
esac

# --------------------------------------------------
# Docker build & run
# --------------------------------------------------
echo
echo ":::::::::::::::::::::: Starting Docker ($ENVIRONMENT) ::::::::::::::::::::::"
echo

chmod +x deploy/entrypoint.sh || true
chmod +x deploy/jibri/finalize.sh || true

COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 \
docker compose "${FILES[@]}" up -d --build

# --------------------------------------------------
# Readiness checks
# --------------------------------------------------
wait_for_app || true
wait_for_jitsi || true
wait_for_tcp localhost 6379 "Redis tcp:6379" || true

# --------------------------------------------------
# Final output
# --------------------------------------------------
echo
echo "✅ Deployment completed: $ENVIRONMENT"
echo

if [[ "$ENVIRONMENT" == "onehost-prod" ]]; then
  echo "- App:   https://${CRVS_APP_DOMAIN}"
  echo "- Jitsi: https://${CRVS_JITSI_DOMAIN}"
else
  echo "- App:   http://localhost"
  echo "- Jitsi: https://localhost:8443"
fi

echo "- Recordings: http://localhost/recordings/"
echo
