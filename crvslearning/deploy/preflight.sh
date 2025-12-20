#!/usr/bin/env bash
# Preflight checks for CRVS one-host deployment (PROD-SAFE)

set -euo pipefail

ENVIRONMENT=${ENVIRONMENT:-dev}

sleep_if_non_ci() {
  local secs=${1:-3}
  if [[ -z "${CI:-}" ]]; then
    sleep "$secs"
  fi
}

echo
echo -e "\033[32m:::::::::: Preflight checks ::::::::::\033[0m"
echo

#############################################
# DOCKER STOP (SAFE MODE)
#############################################

if docker ps -aq >/dev/null 2>&1 && [[ -n "$(docker ps -aq)" ]]; then

  if [[ "$ENVIRONMENT" == "onehost-prod" ]] && [[ "${CRVS_ALLOW_DOCKER_STOP:-0}" != "1" ]]; then
    echo -e "\033[33m⚠ Docker containers detected but docker stop is BLOCKED in PROD\033[0m"
    echo "➡ To allow it explicitly:"
    echo "   CRVS_ALLOW_DOCKER_STOP=1 ./deploy/deploy.sh onehost-prod"
  else
    echo -e "\033[32mStopping running Docker containers...\033[0m"
    docker stop $(docker ps -aq) || true
    sleep_if_non_ci 5
  fi

else
  echo "No running containers to stop."
fi

#############################################
# PORT CHECKS
#############################################

projectPorts=(80 443 6379 8000 8080 8081 8443 10000)

if ! command -v lsof >/dev/null 2>&1; then
  echo -e "\033[33mWarning:\033[0m 'lsof' not found. Port checks skipped."
  exit 0
fi

for port in "${projectPorts[@]}"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN -iUDP:"$port" >/dev/null 2>&1; then
    echo -e "❌ Port $port is already in use"
    echo "Run: lsof -nP -iTCP:$port -sTCP:LISTEN -iUDP:$port"
    exit 1
  else
    echo -e "✅ Port $port available"
  fi
done

echo -e "\n\033[32mPreflight checks passed.\033[0m\n"
