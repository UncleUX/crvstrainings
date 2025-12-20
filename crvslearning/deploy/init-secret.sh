#!/usr/bin/env bash
set -e

ENV_FILE="/.env"

if ! grep -q "^SECRET_KEY=" "$ENV_FILE"; then
  echo "🔐 Génération de SECRET_KEY..."
  echo "SECRET_KEY=$(openssl rand -base64 64)" >> "$ENV_FILE"
else
  echo "ℹ️ SECRET_KEY déjà présent, inchangé"
fi
