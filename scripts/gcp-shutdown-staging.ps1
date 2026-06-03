# Delete Cloud Run staging (stops API billing; keeps images in Artifact Registry)
# Usage: powershell -File scripts/gcp-shutdown-staging.ps1

$ErrorActionPreference = "Stop"
$Region = if ($env:REGION) { $env:REGION } else { "europe-west1" }
$Service = "fieldiq-staging"

Write-Host "Deleting Cloud Run service $Service in $Region ..."
gcloud run services delete $Service --region=$Region --quiet

Write-Host ""
Write-Host "Done. Cloud Run cost for FieldIQ staging is now ~`$0."
Write-Host "Redeploy anytime: gcloud builds submit --config=cloudbuild.yaml ."
Write-Host "Artifact Registry storage is a few cents/month until you delete old images."
