# Build, test, deploy FieldIQ staging on GCP (Windows)
# Usage: powershell -File scripts/gcp-deploy-staging.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$project = gcloud config get-value project 2>$null
if (-not $project -or $project -eq "(unset)") {
    Write-Error "No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
}

Write-Host "Cloud Build -> staging deploy (project: $project)"
gcloud builds submit --config=cloudbuild.yaml .

$region = if ($env:REGION) { $env:REGION } else { "europe-west1" }
$url = gcloud run services describe fieldiq-staging --region=$region --format="value(status.url)" 2>$null

Write-Host ""
Write-Host "Deploy finished."
if ($url) {
    Write-Host "  Health:  $url/health"
    Write-Host "  Swagger: $url/docs"
}
