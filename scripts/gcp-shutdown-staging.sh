#!/usr/bin/env bash
# Delete Cloud Run staging — stops API charges
set -euo pipefail
REGION="${REGION:-europe-west1}"
gcloud run services delete fieldiq-staging --region="$REGION" --quiet
echo "Cloud Run staging removed. Redeploy: gcloud builds submit --config=cloudbuild.yaml ."
