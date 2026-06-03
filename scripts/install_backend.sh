#!/usr/bin/env bash
# Install FieldIQ backend deps with PyTorch from Google Deep Learning Containers guidance.
# For Docker deploy, PyTorch is pre-installed in the Google DLC base image.
# For local dev, install CPU wheels (reliable on Windows vs default PyPI torch).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

echo "Installing application dependencies..."
pip install -r requirements.txt

if python -c "import torch" 2>/dev/null; then
  echo "PyTorch already installed: $(python -c 'import torch; print(torch.__version__)')"
else
  echo "Installing PyTorch CPU wheels (PyTorch.org CPU index)..."
  pip install -r requirements-pytorch-cpu.txt
fi

echo "Done. Verify: python -c \"import torch; print('torch', torch.__version__)\""
