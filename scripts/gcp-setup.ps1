# One-time GCP setup for FieldIQ staging (Windows)
# Usage: powershell -File scripts/gcp-setup.ps1 -ProjectId YOUR_GCP_PROJECT_ID

param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,
    [string]$Region = "europe-west1",
    [string]$Repo = "fieldiq"
)

$ErrorActionPreference = "Stop"

Write-Host "Setting project: $ProjectId"
gcloud config set project $ProjectId

Write-Host "Enabling APIs..."
gcloud services enable artifactregistry.googleapis.com,cloudbuild.googleapis.com,run.googleapis.com,secretmanager.googleapis.com

$exists = gcloud artifacts repositories describe $Repo --location=$Region 2>$null
if (-not $exists) {
    gcloud artifacts repositories create $Repo `
        --repository-format=docker `
        --location=$Region `
        --description="FieldIQ Docker images"
} else {
    Write-Host "Artifact Registry repo already exists."
}

$projectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$cbSa = "${projectNumber}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cbSa" --role="roles/run.admin" --quiet | Out-Null
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cbSa" --role="roles/iam.serviceAccountUser" --quiet | Out-Null

Write-Host ""
Write-Host "GCP setup complete."
Write-Host "Next: gcloud builds submit --config=cloudbuild.yaml ."
