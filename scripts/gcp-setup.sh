#!/usr/bin/env bash
# One-time GCP setup for FieldIQ staging (Cloud Build + Artifact Registry + Cloud Run)
# Usage: ./scripts/gcp-setup.sh YOUR_GCP_PROJECT_ID

set -euo pipefail

PROJECT_ID="${1:-}"
REGION="${REGION:-europe-west1}"
REPO="${REPO:-fieldiq}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 YOUR_GCP_PROJECT_ID"
  echo "Optional env: REGION=europe-west1 REPO=fieldiq"
  exit 1
fi

echo "▶ Setting project: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

echo "▶ Enabling APIs..."
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com

echo "▶ Creating Artifact Registry repo ($REPO in $REGION)..."
if gcloud artifacts repositories describe "$REPO" --location="$REGION" &>/dev/null; then
  echo "   Repository already exists."
else
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="FieldIQ Docker images"
fi

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

echo "▶ Granting Cloud Build permission to deploy Cloud Run..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/run.admin" \
  --quiet >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/iam.serviceAccountUser" \
  --quiet >/dev/null

echo "▶ Reminder: set a billing budget alert in GCP Console (recommended: \$5)"
echo ""
echo "✅ GCP setup complete."
echo ""
echo "Next — deploy staging:"
echo "  gcloud builds submit --config=cloudbuild.yaml ."
echo ""
echo "Or:"
echo "  ./scripts/gcp-deploy-staging.sh"
echo ""
echo "Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"
