# FieldIQ backend — Google Cloud Deep Learning Container (PyTorch 2.3, CUDA 12.1)
# Pre-built, tested PyTorch stack from Google — avoids broken pip wheels on Windows.
# Image docs: https://cloud.google.com/deep-learning-containers/docs/choosing-container
FROM us-docker.pkg.dev/deeplearning-platform-release/gcr.io/pytorch-cu121.2-3.py310

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    CUDA_VISIBLE_DEVICES=""

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt && \
    python -c "import httpx; print('httpx OK', httpx.__version__)"

COPY . .
RUN mkdir -p /app/data/models /app/data/statsbomb /app/data/training && \
    chmod +x /app/docker-entrypoint.sh

# Bake v3 weights once at image build (avoids 4x training on Cloud Run cold start)
ENV MODEL_PATH=/app/data/models/match_mlp.pt \
    SCALER_PATH=/app/data/models/scaler.joblib \
    BOOTSTRAP_EPOCHS=15
RUN python -c "from app.core.model_init import init_model; init_model()"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=120s \
    CMD sh -c 'curl -f http://localhost:${PORT:-8080}/health || exit 1'

ENTRYPOINT ["/app/docker-entrypoint.sh"]
