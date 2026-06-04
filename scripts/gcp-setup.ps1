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
gcloud services enable serviceusage.googleapis.com,storage.googleapis.com,artifactregistry.googleapis.com,cloudbuild.googleapis.com,run.googleapis.com,secretmanager.googleapis.com

$exists = gcloud artifacts repositories describe $Repo --location=$Region 2>$null
if (-not $exists) {
    gcloud artifacts repositories create $Repo `
        --repository-format=docker `
        --location=$Region `
        --description="FieldIQ Docker images"
} else {
    Write-Host "Artifact Registry repo already exists."
}

$Account = gcloud config get-value account 2>$null
$projectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$cbSa = "${projectNumber}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cbSa" --role="roles/run.admin" --quiet | Out-Null
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cbSa" --role="roles/iam.serviceAccountUser" --quiet | Out-Null
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cbSa" --role="roles/storage.admin" --quiet | Out-Null
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cbSa" --role="roles/artifactregistry.writer" --quiet | Out-Null

if ($Account -and $Account -ne "(unset)") {
    Write-Host "IAM for deploy user $Account..."
    gcloud projects add-iam-policy-binding $ProjectId --member="user:$Account" --role="roles/serviceusage.serviceUsageConsumer" --quiet 2>$null | Out-Null
    gcloud projects add-iam-policy-binding $ProjectId --member="user:$Account" --role="roles/cloudbuild.builds.editor" --quiet 2>$null | Out-Null
    gcloud projects add-iam-policy-binding $ProjectId --member="user:$Account" --role="roles/storage.admin" --quiet 2>$null | Out-Null
}

$bucket = "${ProjectId}_cloudbuild"
if (-not (gsutil ls -b "gs://$bucket" 2>$null)) {
    Write-Host "Creating Cloud Build bucket gs://$bucket ..."
    gsutil mb -p $ProjectId -l $Region "gs://$bucket/" 2>$null
}

Write-Host ""
Write-Host "GCP setup complete."
Write-Host "Next: gcloud builds submit --config=cloudbuild.yaml ."
