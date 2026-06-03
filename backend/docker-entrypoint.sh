#!/bin/sh
set -e
# Cloud Run sets PORT=8080; local Docker Compose uses 8000
PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
