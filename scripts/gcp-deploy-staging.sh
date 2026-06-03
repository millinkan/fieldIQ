#!/usr/bin/env bash
# Build, test, and deploy FieldIQ API to Cloud Run staging
# Usage: ./scripts/gcp-deploy-staging.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "❌ No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "▶ Cloud Build → test → push → Cloud Run staging"
echo "   Project: $PROJECT_ID"
gcloud builds submit --config=cloudbuild.yaml .

URL="$(gcloud run services describe fieldiq-staging \
  --region="${REGION:-europe-west1}" \
  --format='value(status.url)' 2>/dev/null || true)"

echo ""
echo "✅ Deploy finished."
if [[ -n "$URL" ]]; then
  echo "   Health:  ${URL}/health"
  echo "   Swagger: ${URL}/docs"
  echo ""
  echo "Quick test:"
  echo "  curl ${URL}/health"
  echo "  curl -H 'X-API-Key: demo' ${URL}/v1/v3/psychological/BRA"
fi
