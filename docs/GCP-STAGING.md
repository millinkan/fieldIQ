# FieldIQ — GCP Staging (build & test)

Use **GCP for staging only**. Production deploys to **Hetzner** later.

```
GitHub → Cloud Build → Artifact Registry → Cloud Run (fieldiq-staging)
                                              ↓
                                    test /health /docs /v1/*
```

## Cost control (GCP will NOT run dry if you follow this)

**Idle Cloud Run = ~$0.** You only pay for builds and active requests.

| Safeguard | This repo |
|-----------|-----------|
| `min-instances: 0` | Yes — in `cloudbuild.yaml` |
| `max-instances: 1` | Yes — staging cap |
| `cpu: 1` | Yes — not 2 vCPU |
| CPU throttling when idle | Yes |
| No 24/7 VM / GPU / GKE | You only use Cloud Build + Run |
| MC cap on staging | `MC_SIMULATIONS=1000` env |

### Do this once (5 minutes)

1. GCP Console → **Billing** → **Budgets** → create **$5** budget with email alerts at 50%, 90%, 100%  
2. After deploy, verify:

```bash
./scripts/gcp-cost-check.sh
# Windows:
powershell -File scripts/gcp-cost-check.ps1
```

### Stop GCP charges when not testing

```bash
./scripts/gcp-shutdown-staging.sh
# Windows:
powershell -File scripts/gcp-shutdown-staging.ps1
```

Deletes Cloud Run only (~$0). Images stay in Artifact Registry (pennies). Redeploy with `gcloud builds submit` anytime.

### Expected spend (light staging use)

| Activity | ~Cost/month |
|----------|-------------|
| Cloud Run idle | **$0** |
| 3–5 deploys | **$0–2** |
| Casual API tests | **$0–2** |
| **Total typical** | **Under $5** |

### Never do on GCP (these drain accounts)

- `min-instances: 1` or higher on Cloud Run  
- Leaving a Compute Engine / GPU VM running  
- Vertex AI GPU training left on  
- Memorystore Redis  
- Heavy 10k simulations all day

First deploy builds the Google PyTorch DLC image (~5–10 min). Later deploys are faster.

---

## Prerequisites

1. [Google Cloud account](https://cloud.google.com/) with billing enabled  
2. [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and logged in:

```bash
gcloud auth login
gcloud auth application-default login   # optional, for local tools
```

3. Clone the repo:

```bash
git clone https://github.com/millinkan/fieldIQ.git
cd fieldIQ
```

---

## Step 1 — One-time GCP setup

Replace `YOUR_GCP_PROJECT_ID` with your project ID.

**Linux / macOS / Cloud Shell:**

```bash
chmod +x scripts/gcp-setup.sh scripts/gcp-deploy-staging.sh
./scripts/gcp-setup.sh YOUR_GCP_PROJECT_ID
```

**Windows (PowerShell):**

```powershell
powershell -File scripts/gcp-setup.ps1 -ProjectId YOUR_GCP_PROJECT_ID
```

This enables Artifact Registry, Cloud Build, Cloud Run and creates the `fieldiq` Docker repo in `europe-west1` (close to Hetzner EU).

---

## Step 2 — Deploy staging

From repo root:

```bash
gcloud builds submit --config=cloudbuild.yaml .
```

Or use the helper script:

```bash
./scripts/gcp-deploy-staging.sh
```

**Windows:**

```powershell
powershell -File scripts/gcp-deploy-staging.ps1
```

Cloud Build will:

1. Build `backend/Dockerfile` (Google PyTorch DLC base)  
2. Run `pytest` with `SKIP_MODEL_INIT=1`  
3. Push image to Artifact Registry  
4. Deploy **fieldiq-staging** on Cloud Run (4 GiB RAM, scales to zero)

---

## Step 3 — Get your staging URL

```bash
gcloud run services describe fieldiq-staging \
  --region=europe-west1 \
  --format='value(status.url)'
```

Example checks:

```bash
STAGING=https://fieldiq-staging-xxxxx-ew.a.run.app

curl "$STAGING/health"
curl -H "X-API-Key: demo" "$STAGING/v1/tournament/teams"
curl -H "X-API-Key: demo" "$STAGING/v1/v3/psychological/BRA"
```

Open Swagger: `{STAGING_URL}/docs`

> **Note:** Staging is **API only** (no nginx frontend). Use Swagger or curl. Full UI runs on Hetzner via `docker compose`.

---

## Step 4 — Connect GitHub (optional auto-deploy)

1. GCP Console → **Cloud Build** → **Triggers** → **Create trigger**  
2. Connect repository: `millinkan/fieldIQ`  
3. Event: Push to branch `main` (or `staging`)  
4. Config: Cloud Build configuration file → `cloudbuild.yaml`  
5. Save  

Every push to that branch rebuilds and redeploys staging.

---

## Environment variables (staging)

Set in `cloudbuild.yaml` deploy step or update later:

```bash
gcloud run services update fieldiq-staging \
  --region=europe-west1 \
  --set-env-vars "LIVE_DATA_PROVIDER=mock,LOG_LEVEL=INFO"
```

For API keys, use Secret Manager:

```bash
echo -n "your-key" | gcloud secrets create API_SPORTS_KEY --data-file=-
gcloud run services update fieldiq-staging \
  --region=europe-west1 \
  --set-secrets API_SPORTS_KEY=API_SPORTS_KEY:latest
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'httpx'` | Redeploy with `gcloud builds submit --config=cloudbuild.yaml .` (uses Dockerfile + `requirements-prod.txt`). Do not use Console “deploy from source” without our Dockerfile unless root `requirements.txt` is present. |
| Cloud Build permission denied on deploy | Re-run `./scripts/gcp-setup.sh` (grants Cloud Build → Cloud Run) |
| First request 503 / slow | Cold start + model init (~1–2 min); retry `/health` |
| Port 8080 vs 8000 | Cloud Run uses **8080**; image entrypoint reads `$PORT` |
| 4 workers training on startup | Fixed: `--workers 1` + model **baked in Docker build** (not at request time) |
| Logs show `bootstrapping v3` every cold start | Redeploy with latest Dockerfile — should say `Loading saved v3 model` |
| Tests pass locally, fail in Cloud Build | Check Cloud Build logs; same image runs pytest |
| `Artifact Registry` not found | Run setup script or create repo manually in Console |
| Build timeout | Default is 10 min; increase in trigger settings if needed |

View logs:

```bash
gcloud builds list --limit=5
gcloud builds log BUILD_ID
gcloud run services logs read fieldiq-staging --region=europe-west1
```

---

## Next: Hetzner production

After staging looks good:

1. SSH to Hetzner VPS  
2. `git clone` + `docker compose up -d` (full UI + API + Redis)  
3. See `README.md` Quick Start  

GCP staging URL = test. Hetzner = live.
