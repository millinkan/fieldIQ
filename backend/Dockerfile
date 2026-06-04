# FieldIQ — API image with baked dashboard (Vite → /app/static)
# Build from repo root: docker build -f backend/Dockerfile .
# Uses python:slim + CPU PyTorch (reliable in Cloud Build; DLC image is ~10GB and often fails).

# ── Frontend (Vite) ──────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install
COPY frontend/ ./
RUN npm run build

# ── Backend ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    CUDA_VISIBLE_DEVICES="" \
    SERVE_FRONTEND=true \
    STATIC_DIR=/app/static

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential && \
    rm -rf /var/lib/apt/lists/*

# PyTorch CPU wheels first (not in requirements-prod.txt)
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt && \
    python -c "import httpx, torch; print('httpx', httpx.__version__, 'torch', torch.__version__)"

COPY backend/ .
COPY --from=frontend /fe/dist /app/static
RUN mkdir -p /app/data/models /app/data/statsbomb /app/data/training && \
    chmod +x /app/docker-entrypoint.sh

ENV MODEL_PATH=/app/data/models/match_mlp.pt \
    SCALER_PATH=/app/data/models/scaler.joblib \
    BOOTSTRAP_EPOCHS=5
RUN python -c "from app.core.model_init import init_model; init_model()"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=120s \
    CMD sh -c 'curl -f http://localhost:${PORT:-8080}/health || exit 1'

ENTRYPOINT ["/app/docker-entrypoint.sh"]
