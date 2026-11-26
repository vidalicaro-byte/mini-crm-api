#!/bin/sh
# Container start: migrate, load the demo data on a fresh database, then serve.
# (Render's free plan has no pre-deploy step, so migrations run here; they are idempotent.)
set -e

alembic upgrade head
python -m crm_api.seed --if-empty

# --proxy-headers: Render terminates HTTPS in front of the app; trust its X-Forwarded-* headers.
exec uvicorn crm_api.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips "*"
