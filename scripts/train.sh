#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# FieldIQ — Bootstrap Training Script
# Runs the three-phase training pipeline inside the running backend container.
#
# Usage:
#   ./scripts/train.sh           # Phase 1: StatsBomb open data (free)
#   ./scripts/train.sh 2         # Phase 2: + live API (API-Sports/Sportmonks)
#   ./scripts/train.sh 3         # Phase 3: + FootyStats premium
#   ./scripts/train.sh 1 --force # Force re-train even if weights exist
# ────────────────────────────────────────────────────────────────────────────

set -e
PHASE="${1:-1}"
EXTRA="${2:-}"
CONTAINER="fieldiq-api"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FieldIQ Training Pipeline — Phase ${PHASE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PHASE_DESC=(
  [1]="StatsBomb open data (FREE — ~4,000 real matches)"
  [2]="+ Live API augmentation (API-Sports / Sportmonks free tier)"
  [3]="+ FootyStats premium enrichment (requires paid key)"
)
echo "  Source: ${PHASE_DESC[$PHASE]}"
echo ""

# Check container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "  ⚠  Container '${CONTAINER}' is not running."
  echo "  Run ./deploy.sh dev first, then re-run this script."
  exit 1
fi

# Phase 1: Clone StatsBomb repo (if needed)
if [ "$PHASE" -ge "1" ]; then
  echo "  → Checking StatsBomb open-data repo..."
  docker exec "$CONTAINER" bash -c "
    if [ ! -d /app/data/statsbomb/.git ]; then
      echo '  Cloning StatsBomb open-data (shallow clone ~150 MB)...'
      git clone --filter=blob:none --depth=1 \
        https://github.com/statsbomb/open-data.git \
        /app/data/statsbomb
    else
      echo '  Repo present — pulling latest...'
      git -C /app/data/statsbomb pull --quiet
    fi
  "
fi

# Phase 2/3: Check API keys
if [ "$PHASE" -ge "2" ]; then
  echo ""
  echo "  → Phase 2 requires a live API key."
  echo "     Set API_SPORTS_KEY or SPORTMONKS_KEY in .env"
  echo "     API-Sports free signup: https://api-sports.io"
  echo "     Sportmonks free signup: https://sportmonks.com"
fi

if [ "$PHASE" -ge "3" ]; then
  echo ""
  echo "  → Phase 3 requires a FootyStats paid key."
  echo "     Set FOOTYSTATS_API_KEY in .env"
  echo "     FootyStats signup: https://footystats.org/api"
fi

echo ""
echo "  → Running training pipeline..."
docker exec "$CONTAINER" python -m app.training.train_pipeline \
  --phase "$PHASE" $EXTRA

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Phase ${PHASE} training complete"
echo "     New weights are live immediately — no restart needed."
echo "     Check /v1/model/train/status for the training report."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
