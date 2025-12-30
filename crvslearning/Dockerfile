# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn uvicorn daphne channels-redis

# Project files
COPY . /app

# Django collectstatic at build time optionally (disabled by default)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Entry point (will run migrations + start server)
RUN chmod +x /app/deploy/entrypoint.sh || true
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
