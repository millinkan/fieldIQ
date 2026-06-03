# Verify FieldIQ staging is cost-safe on GCP (scale-to-zero, no min instances)
# Usage: powershell -File scripts/gcp-cost-check.ps1

$ErrorActionPreference = "Stop"
$Region = if ($env:REGION) { $env:REGION } else { "europe-west1" }
$Service = "fieldiq-staging"

$project = gcloud config get-value project 2>$null
if (-not $project -or $project -eq "(unset)") {
    Write-Error "Run: gcloud config set project YOUR_GCP_PROJECT_ID"
}

Write-Host "Project: $project"
Write-Host "Checking Cloud Run service: $Service ($Region)"
Write-Host ""

$exists = gcloud run services describe $Service --region=$Region 2>$null
if (-not $exists) {
    Write-Host "OK — Cloud Run service not deployed (GCP idle cost ~`$0 for Run)."
    exit 0
}

$json = gcloud run services describe $Service --region=$Region --format=json | ConvertFrom-Json
$template = $json.spec.template
$containers = $template.spec.containers[0]
$ann = $template.metadata.annotations

$minScale = $ann.'autoscaling.knative.dev/minScale'
$maxScale = $ann.'autoscaling.knative.dev/maxScale'
$memory = $containers.resources.limits.memory
$cpu = $containers.resources.limits.cpu

Write-Host "  min-instances (minScale): $minScale"
Write-Host "  max-instances (maxScale): $maxScale"
Write-Host "  memory: $memory"
Write-Host "  cpu: $cpu"
Write-Host ""

$ok = $true
if ($minScale -and $minScale -ne "0") {
    Write-Host "WARN — min-instances > 0 bills 24/7. Set to 0:" -ForegroundColor Yellow
    Write-Host "  gcloud run services update $Service --region=$Region --min-instances=0"
    $ok = $false
}
if ($maxScale -and [int]$maxScale -gt 2) {
    Write-Host "WARN — max-instances is high ($maxScale). Staging uses 1." -ForegroundColor Yellow
}

if ($ok) {
    Write-Host "OK — Staging looks cost-safe (scales to zero when idle)." -ForegroundColor Green
    Write-Host "Set a `$5 billing budget: GCP Console -> Billing -> Budgets"
}

Write-Host ""
Write-Host "Stop all GCP Run charges for this app:"
Write-Host "  powershell -File scripts/gcp-shutdown-staging.ps1"
