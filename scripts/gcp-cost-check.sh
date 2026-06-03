#!/usr/bin/env bash
# Verify FieldIQ staging is cost-safe (min-instances=0)
set -euo pipefail
REGION="${REGION:-europe-west1}"
SERVICE="fieldiq-staging"

if ! gcloud run services describe "$SERVICE" --region="$REGION" &>/dev/null; then
  echo "OK — no Cloud Run service (idle cost ~\$0)."
  exit 0
fi

MIN=$(gcloud run services describe "$SERVICE" --region="$REGION" \
  --format='value(spec.template.metadata.annotations.autoscaling.knative.dev/minScale)')
MAX=$(gcloud run services describe "$SERVICE" --region="$REGION" \
  --format='value(spec.template.metadata.annotations.autoscaling.knative.dev/maxScale)')

echo "minScale=$MIN maxScale=$MAX"
if [[ "$MIN" != "0" && -n "$MIN" ]]; then
  echo "WARN: min-instances > 0 — costs 24/7. Fix:"
  echo "  gcloud run services update $SERVICE --region=$REGION --min-instances=0"
  exit 1
fi
echo "OK — cost-safe (scales to zero)."
