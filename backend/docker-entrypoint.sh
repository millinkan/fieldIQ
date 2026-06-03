#!/bin/sh
set -e
# Cloud Run sets PORT=8080; prevent multi-worker duplicate model training on startup
export WEB_CONCURRENCY=1
PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
