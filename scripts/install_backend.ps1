# Install FieldIQ backend on Windows
# PyTorch: use CPU wheels (fixes Microsoft Store Python DLL issues)
# Docker deploy uses Google Deep Learning Containers instead — see backend/Dockerfile
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"

Write-Host "Installing application dependencies..."
python -m pip install -r requirements.txt

Write-Host "Installing PyTorch CPU wheels (reinstall if broken)..."
python -m pip install --force-reinstall --no-cache-dir -r requirements-pytorch-cpu.txt

python -c "import torch; print('torch OK:', torch.__version__, '| cuda:', torch.cuda.is_available())"
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyTorch failed to load. Use Docker: ./deploy.sh dev"
    exit 1
}
