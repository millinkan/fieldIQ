# GCP push checklist

Use this before every staging deploy. Work from **`fieldiq-pro-v3/fieldiq`** only (not `fieldiq - Copy`).

## 1. Prerequisites (once)

- [ ] [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed
- [ ] `gcloud auth login`
- [ ] Billing enabled on your GCP project
- [ ] One-time setup: `powershell -File scripts/gcp-setup.ps1 -ProjectId YOUR_PROJECT_ID`

```powershell
gcloud config set project fieldiq-498301
```

Or copy `gcp.project.example` → `gcp.project.local` with your project id (already set locally for `fieldiq-498301`, gitignored).

## 2. Pre-flight (every deploy)

- [ ] `backend/requirements-prod.txt` is **not empty** (prod deps, no pytest)
- [ ] Local tests (optional, fast):

```powershell
cd backend
$env:SKIP_MODEL_INIT="1"
python -m pytest tests/ -q
```

- [ ] Commit and push to GitHub (optional if deploying from local only):

```powershell
cd ..\..   # repo root fieldiq/
git status
git push origin main
```

## 3. Deploy

From repo root **`fieldiq-pro-v3/fieldiq`**:

```powershell
powershell -File scripts/gcp-deploy-staging.ps1
```

Or:

```powershell
gcloud builds submit --config=cloudbuild.yaml .
```

Wait for: `build-api` → `test-api` → `push-api` → `deploy-staging` (all green).

## 4. Verify

```powershell
$url = gcloud run services describe fieldiq-staging --region=europe-west1 --format="value(status.url)"
Write-Host "URL: $url"
Invoke-WebRequest "$url/health" | Select-Object StatusCode, Content
```

In browser:

| URL | Expect |
|-----|--------|
| `{url}/` | FieldIQ dashboard (Command + Deep tabs) |
| `{url}/health` | JSON `status: ok`, `features: 35` |
| `{url}/docs` | Swagger UI |

Logs should show **one worker** and **Loading saved v3 model** (not four parallel bootstraps).

## 5. Stop spend when done

```powershell
powershell -File scripts/gcp-shutdown-staging.ps1
```

Redeploy anytime with step 3.

## What gets deployed

| Item | Value |
|------|--------|
| Service | `fieldiq-staging` |
| Region | `europe-west1` |
| Port | `8080` |
| Min instances | `0` (scale to zero) |
| Max instances | `1` |
| Image | Artifact Registry `fieldiq/api` |

Full details: [GCP-STAGING.md](./GCP-STAGING.md)
