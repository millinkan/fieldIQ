#!/usr/bin/env bash
# Fix: forbidden from accessing bucket PROJECT_ID_cloudbuild
# Usage: ./scripts/gcp-fix-build-permissions.sh fieldiq-498301

set -euo pipefail

PROJECT_ID="${1:-}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 YOUR_GCP_PROJECT_ID"
  exit 1
fi

REGION="${REGION:-europe-west1}"
BUCKET="${PROJECT_ID}_cloudbuild"
ACCOUNT="$(gcloud config get-value account 2>/dev/null || true)"

echo "▶ Project: $PROJECT_ID"
echo "▶ Account: ${ACCOUNT:-unknown}"
gcloud config set project "$PROJECT_ID"

echo "▶ Enabling APIs (including Storage + Service Usage)..."
gcloud services enable \
  serviceusage.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
GCS_SA="${PROJECT_NUMBER}@gs-project-accounts.iam.gserviceaccount.com"

echo "▶ IAM for your user ($ACCOUNT)..."
if [[ -n "$ACCOUNT" && "$ACCOUNT" != "(unset)" ]]; then
  for ROLE in \
    roles/serviceusage.serviceUsageConsumer \
    roles/cloudbuild.builds.editor \
    roles/storage.admin; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="user:${ACCOUNT}" \
      --role="$ROLE" \
      --quiet >/dev/null || true
  done
fi

echo "▶ IAM for Cloud Build service account..."
for ROLE in \
  roles/storage.admin \
  roles/artifactregistry.writer \
  roles/run.admin \
  roles/iam.serviceAccountUser \
  roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CB_SA}" \
    --role="$ROLE" \
    --quiet >/dev/null || true
done

echo "▶ Ensuring default Cloud Build bucket gs://${BUCKET} ..."
if gsutil ls -b "gs://${BUCKET}" &>/dev/null; then
  echo "   Bucket exists."
else
  gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${BUCKET}/" || true
fi

echo "▶ Bucket ACL for Cloud Build + GCS service agents..."
gsutil iam ch "serviceAccount:${CB_SA}:roles/storage.admin" "gs://${BUCKET}" 2>/dev/null || true
gsutil iam ch "serviceAccount:${GCS_SA}:roles/storage.admin" "gs://${BUCKET}" 2>/dev/null || true

echo ""
echo "✅ Permissions updated. Wait ~60 seconds, then:"
echo "   gcloud builds submit --config=cloudbuild.yaml ."
echo ""
echo "If it still fails, you may need Project Owner/Editor on fieldiq-498301"
echo "or an org admin to lift a storage restriction policy."
