#!/usr/bin/env sh
# See backend-django/start.sh for why this is a file and not an inline command.
set -e

# No --reload, and the port comes from the platform. The Dockerfile CMD hardcodes
# 8001 with the reloader on, which is right for docker-compose and wrong here.
# uvicorn does not read $PORT itself, so it is passed explicitly.
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8001}"
