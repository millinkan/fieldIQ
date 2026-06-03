# FieldIQ — API image with optional baked dashboard (Vite → /app/static)
# Build from repo root: docker build -f backend/Dockerfile .

# ── Frontend (Vite) ──────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Backend (Google Deep Learning Container + PyTorch) ───────────────────────
FROM us-docker.pkg.dev/deeplearning-platform-release/gcr.io/pytorch-cu121.2-3.py310

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    CUDA_VISIBLE_DEVICES="" \
    SERVE_FRONTEND=true \
    STATIC_DIR=/app/static

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl git && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements-prod.txt backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt && \
    python -c "import httpx; print('httpx OK', httpx.__version__)"

COPY backend/ .
COPY --from=frontend /fe/dist /app/static
RUN mkdir -p /app/data/models /app/data/statsbomb /app/data/training && \
    chmod +x /app/docker-entrypoint.sh

ENV MODEL_PATH=/app/data/models/match_mlp.pt \
    SCALER_PATH=/app/data/models/scaler.joblib \
    BOOTSTRAP_EPOCHS=15
RUN python -c "from app.core.model_init import init_model; init_model()"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=120s \
    CMD sh -c 'curl -f http://localhost:${PORT:-8080}/health || exit 1'

ENTRYPOINT ["/app/docker-entrypoint.sh"]
