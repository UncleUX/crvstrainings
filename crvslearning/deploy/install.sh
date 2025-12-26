#!/usr/bin/env bash
# --------------------------------------------------
# CRVS Bootstrap Installer (PROD-SAFE)
#
# Usage:
#   ./install-crvs.sh                -> onehost-dev (default)
#   ./install-crvs.sh onehost-dev
#   ./install-crvs.sh onehost-prod
#
# One-liner:
#   curl -fsSL <URL>/install-crvs.sh | sudo bash -s onehost-prod
# --------------------------------------------------

set -euo pipefail

# --------------------------------------------------
# Environment selection
# --------------------------------------------------
ENVIRONMENT="${1:-onehost-dev}"

case "$ENVIRONMENT" in
  onehost-dev|onehost-prod)
    ;;
  *)
    echo "❌ Invalid environment: $ENVIRONMENT"
    echo "Allowed values: onehost-dev | onehost-prod"
    exit 1
    ;;
esac

echo "🔧 Bootstrapping CRVS server"
echo "➡️ Environment: $ENVIRONMENT"
echo

# --------------------------------------------------
# PROD SAFETY CONFIRMATION
# --------------------------------------------------
if [[ "$ENVIRONMENT" == "onehost-prod" ]]; then
  echo "⚠️  WARNING: You are deploying to PRODUCTION"
  echo "This may start/replace production services."
  echo
  read -r -p "Type 'DEPLOY-PROD' to continue: " CONFIRM
  if [[ "$CONFIRM" != "DEPLOY-PROD" ]]; then
    echo "❌ Production deployment aborted"
    exit 1
  fi
fi

# --------------------------------------------------
# Require root
# --------------------------------------------------
if [[ "$EUID" -ne 0 ]]; then
  echo "❌ This installer must be run as root (use sudo)"
  exit 1
fi

# --------------------------------------------------
# Install Docker (official, with buildx)
# --------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  echo "🐳 Installing Docker (official)..."
  curl -fsSL https://get.docker.com | sh
else
  echo "🐳 Docker already installed"
fi

# --------------------------------------------------
# Install Git
# --------------------------------------------------
if ! command -v git >/dev/null 2>&1; then
  echo "📦 Installing Git..."
  apt-get update
  apt-get install -y git
else
  echo "📦 Git already installed"
fi

# --------------------------------------------------
# Verify Docker is usable
# --------------------------------------------------
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker is installed but not running"
  exit 1
fi

# --------------------------------------------------
# Clone repository (persistent)
# --------------------------------------------------
INSTALL_DIR="/opt/crvs"
REPO_URL="git@github.com:UncleUX/crvstrainings.git"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [[ ! -d crvstrainings/.git ]]; then
  echo "📥 Cloning CRVS repository..."
  git clone "$REPO_URL" crvstrainings
else
  echo "📂 Repository already exists"
fi

cd crvstrainings

# --------------------------------------------------
# Deploy
# --------------------------------------------------
echo
echo "🚀 Running deployment script..."
./deploy/deploy.sh "$ENVIRONMENT"

# --------------------------------------------------
# Final
# --------------------------------------------------
echo
echo "✅ CRVS deployment finished successfully"
echo "📍 Location: $INSTALL_DIR/crvstrainings"
echo "🌍 Environment: $ENVIRONMENT"
echo
