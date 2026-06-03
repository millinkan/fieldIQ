# FieldIQ backend — Google Cloud Deep Learning Container (PyTorch 2.3, CUDA 12.1)
# Pre-built, tested PyTorch stack from Google — avoids broken pip wheels on Windows.
# Image docs: https://cloud.google.com/deep-learning-containers/docs/choosing-container
FROM us-docker.pkg.dev/deeplearning-platform-release/gcr.io/pytorch-cu121.2-3.py310

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # CPU inference by default in compose; GPU available when nvidia-runtime is attached
    CUDA_VISIBLE_DEVICES=""

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data/models /app/data/statsbomb /app/data/training

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
