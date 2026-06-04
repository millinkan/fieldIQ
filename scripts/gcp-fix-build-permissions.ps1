# Fix: forbidden from accessing bucket PROJECT_ID_cloudbuild
# Usage: powershell -File scripts/gcp-fix-build-permissions.ps1 -ProjectId fieldiq-498301

param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,
    [string]$Region = "europe-west1"
)

$ErrorActionPreference = "Stop"
$Bucket = "${ProjectId}_cloudbuild"
$Account = gcloud config get-value account 2>$null

Write-Host "Project: $ProjectId"
Write-Host "Account: $Account"
gcloud config set project $ProjectId | Out-Null

Write-Host "Enabling APIs..."
gcloud services enable serviceusage.googleapis.com,storage.googleapis.com,cloudbuild.googleapis.com,artifactregistry.googleapis.com,run.googleapis.com

$projectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$cbSa = "${projectNumber}@cloudbuild.gserviceaccount.com"
$gcsSa = "${projectNumber}@gs-project-accounts.iam.gserviceaccount.com"

function Bind-Role($Member, $Role) {
    gcloud projects add-iam-policy-binding $ProjectId --member=$Member --role=$Role --quiet 2>$null | Out-Null
}

if ($Account -and $Account -ne "(unset)") {
    Write-Host "IAM for user $Account..."
    Bind-Role "user:$Account" "roles/serviceusage.serviceUsageConsumer"
    Bind-Role "user:$Account" "roles/cloudbuild.builds.editor"
    Bind-Role "user:$Account" "roles/storage.admin"
}

Write-Host "IAM for Cloud Build service account..."
foreach ($role in @(
    "roles/storage.admin",
    "roles/artifactregistry.writer",
    "roles/run.admin",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter"
)) {
    Bind-Role "serviceAccount:$cbSa" $role
}

Write-Host "Ensuring bucket gs://$Bucket ..."
$bucketExists = gsutil ls -b "gs://$Bucket" 2>$null
if (-not $bucketExists) {
    gsutil mb -p $ProjectId -l $Region "gs://$Bucket/" 2>$null
}

gsutil iam ch "serviceAccount:${cbSa}:roles/storage.admin" "gs://$Bucket" 2>$null
gsutil iam ch "serviceAccount:${gcsSa}:roles/storage.admin" "gs://$Bucket" 2>$null

Write-Host ""
Write-Host "Done. Wait ~60 seconds, then:"
Write-Host "  gcloud builds submit --config=cloudbuild.yaml ."
