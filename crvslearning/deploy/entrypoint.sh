#!/usr/bin/env bash
set -euo pipefail

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-crvslearning.settings}
export PYTHONUNBUFFERED=1

python manage.py collectstatic --noinput || true
python manage.py migrate --noinput

WORKERS=${WORKERS:-4}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

exec gunicorn \
  -k uvicorn.workers.UvicornWorker \
  -w "$WORKERS" \
  -b "$HOST:$PORT" \
  crvslearning.asgi:application
