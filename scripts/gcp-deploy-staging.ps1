# Build, test, deploy FieldIQ staging on GCP (Windows)
# Usage: powershell -File scripts/gcp-deploy-staging.ps1
#        powershell -File scripts/gcp-deploy-staging.ps1 -ProjectId fieldiq-498301

param([string]$ProjectId = "")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$project = & (Join-Path $PSScriptRoot "gcp-resolve-project.ps1") -ProjectId $ProjectId
if (-not $project) {
    Write-Error "No GCP project. Set gcp.project.local, -ProjectId, or: gcloud config set project YOUR_PROJECT_ID"
}
gcloud config set project $project | Out-Null

Write-Host "Cloud Build -> staging deploy (project: $project)"
gcloud builds submit --config=cloudbuild.yaml .

$region = if ($env:REGION) { $env:REGION } else { "europe-west1" }
$url = gcloud run services describe fieldiq-staging --region=$region --format="value(status.url)" 2>$null

Write-Host ""
Write-Host "Deploy finished."
if ($url) {
    Write-Host "  UI:      $url/"
    Write-Host "  Health:  $url/health"
    Write-Host "  Swagger: $url/docs"
}
