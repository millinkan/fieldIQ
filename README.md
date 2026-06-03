# FieldIQ Pro v3 — WC 2026 Predictive Intelligence Platform

Enterprise-grade football analytics: PyTorch MLP match prediction, 48-team Monte Carlo simulation, PDV discipline engine, SRR bench depth, and five contextual intelligence layers — deployable in one command with full test coverage.

## Competitive Positioning

| Capability | FieldIQ v3 | FootyStats | API-Sports | Sportmonks | Opta/Sportradar |
|------------|-----------|------------|------------|------------|-----------------|
| Match outcome MLP | 35-feature PyTorch | Heuristic models | Odds only | Basic stats | Proprietary |
| Tournament Monte Carlo | 48-team, 10k sims | No | No | No | Custom B2B |
| PDV discipline cascade | Yes | Partial | Cards only | Partial | Event-level |
| SRR bench depth | Dynamic, 48 teams | Squad value only | No | No | Limited |
| Travel/fatigue (WC 2026) | 16 host cities | No | No | No | No |
| Club chemistry (xT) | Yes | No | No | No | Partnership data |
| Multi-provider ingestion | 4 adapters | Single source | Single source | Single source | Closed |
| Self-hosted / API | Both | SaaS only | SaaS only | SaaS only | Enterprise only |

## Architecture

```
fieldiq/
├── backend/                     # FastAPI + PyTorch
│   ├── app/
│   │   ├── api/                 # Route handlers
│   │   ├── core/                # Config, cache, features, model init
│   │   ├── middleware/          # Logging, credits, rate limits
│   │   ├── models/              # MatchMLP (35 → 512 → 256 → 128 → 64 → 3)
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── services/            # Prediction + 4 intelligence engines
│   │   ├── data_pipeline/       # StatsBomb + live API adapters
│   │   └── training/            # 3-phase training pipeline
│   ├── tests/                   # pytest suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                    # Vite + vanilla JS dashboard
├── docker-compose.yml           # backend + frontend + redis + test profile
├── cloudbuild.yaml              # GCP: build → pytest → Cloud Run staging
├── docs/GCP-STAGING.md          # GCP staging setup (test before Hetzner)
├── deploy.sh
└── .env.example
```

## Quick Start

### Prerequisites
- Docker + Docker Compose v2

### Deploy

```bash
cd fieldiq
chmod +x deploy.sh
./deploy.sh dev
```

Visit:
- **Frontend** → http://localhost
- **API Swagger** → http://localhost/docs
- **Health** → http://localhost/health

### Run Tests

```bash
# Local (requires Python 3.10–3.11)
cd backend
./../scripts/install_backend.sh    # Linux/macOS — installs PyTorch CPU wheels
# or on Windows:
#   powershell -File ../scripts/install_backend.ps1
pytest tests/ -v

# Docker (PyTorch from Google Deep Learning Container — recommended)
docker compose --profile test run --rm test
```

## GCP Staging (test before Hetzner production)

Use Google Cloud to **build, test, and host a staging API** — Cloud Run scales to zero when idle (low cost).

```bash
# One-time setup
chmod +x scripts/gcp-setup.sh scripts/gcp-deploy-staging.sh
./scripts/gcp-setup.sh YOUR_GCP_PROJECT_ID

# Build + pytest + deploy Cloud Run staging
gcloud builds submit --config=cloudbuild.yaml .
```

**Windows:** `powershell -File scripts/gcp-setup.ps1 -ProjectId YOUR_GCP_PROJECT_ID`

Full guide: **[docs/GCP-STAGING.md](docs/GCP-STAGING.md)**

**GCP cost safety:** `min-instances=0`, max 1 instance — idle ≈ $0. Set a **$5 billing budget** in GCP Console. When done testing: `powershell -File scripts/gcp-shutdown-staging.ps1`

| Environment | Purpose |
|-------------|---------|
| **GCP Cloud Run** | Staging API — `/docs`, `/v1/*`, auto pytest on build |
| **Hetzner VPS** | Production — full UI + API + Redis (`docker compose up -d`) |
| **Local Docker** | Development — `./deploy.sh dev` |

## PyTorch Installation

FieldIQ uses **Google Cloud Deep Learning Containers** for production Docker builds — a pre-tested PyTorch 2.3 stack (CUDA 12.1, Python 3.10) from Google:

```
us-docker.pkg.dev/deeplearning-platform-release/gcr.io/pytorch-cu121.2-3.py310
```

| Environment | How PyTorch is provided |
|-------------|-------------------------|
| **Docker / deploy** | Pre-installed in Google DLC base image (`backend/Dockerfile`) |
| **Local Windows** | `scripts/install_backend.ps1` → CPU wheels from PyTorch.org |
| **Local Linux/macOS** | `scripts/install_backend.sh` |
| **Local GPU (CUDA 12.1)** | `pip install -r backend/requirements-pytorch-gpu.txt` |

`torch` is intentionally **not** in `requirements.txt`.

**Windows note:** Microsoft Store Python often breaks native PyTorch (`shm.dll`). Use **Docker** (`./deploy.sh dev`) which runs PyTorch from Google's container — or install Python from [python.org](https://www.python.org/downloads/).

Docs: [Google Deep Learning Containers — PyTorch](https://cloud.google.com/deep-learning-containers/docs/choosing-container)

## API Endpoints

| Method | Path | Credits | Description |
|--------|------|---------|-------------|
| POST | `/v1/tournament/simulate` | 10 | Full 48-team Monte Carlo (weights + layer toggles) |
| POST | `/v1/v3/full-analysis` | 5 | Pre-match intelligence report (4 layers) |
| POST | `/v1/squad/synergy` | 3 | Roster-adjusted synergy vector |
| POST | `/v1/pdv/cascade` | 2 | Suspension cascade simulation |
| GET | `/v1/srr/rankings` | 1 | Dynamic Squad Robustness Rating |
| GET | `/v1/v3/psychological/{team_id}` | 2 | Morale vector + circadian overlay context |
| GET | `/v1/v3/psychological/player/{id}` | 1 | Player-level psychological breakdown |
| GET | `/v1/v3/fatigue/{team_id}` | 1 | Travel decay & fatigue analysis |
| GET | `/v1/model/architecture` | 0 | MLP v3 architecture (35 features) |
| POST | `/v1/model/train` | 0 | Trigger training pipeline |
| GET | `/v1/model/fixtures` | 0 | Upcoming fixtures from live provider |
| GET | `/v1/model/injuries/{team_id}` | 0 | Live injury list |
| GET | `/v1/credits/balance` | 0 | Credit pool status |

Pass `X-API-Key: demo` header on all requests.

## Simulation Request

```bash
curl -X POST http://localhost/v1/tournament/simulate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo" \
  -d '{
    "n_simulations": 1000,
    "elo_weight": 0.40,
    "form_weight": 0.25,
    "pdv_weight": 0.20,
    "xg_weight": 0.15,
    "srr_weight": 0.10,
    "enable_fatigue": true,
    "enable_chemistry": true,
    "enable_momentum": true,
    "enable_tactical": true,
    "enable_psychological": true,
    "injuries": {"BRA": ["vinicius", "casemiro"]}
  }'
```

## MLP v3 Architecture

```
Input(35) → Linear(512) → BatchNorm → ReLU → Dropout(0.3)
          → Linear(256) → BatchNorm → ReLU → Dropout(0.3)
          → Linear(128) → BatchNorm → ReLU → Dropout(0.25)
          → Linear(64)  → BatchNorm → ReLU → Dropout(0.2)
          → Linear(3)   → Softmax → [P_win, P_draw, P_loss]
```

Features 0–22: structural (ELO, xG, PDV, SRR, form, etc.)
Features 23–34: v3 intelligence (fatigue, chemistry, momentum, tactical)

## Layer 5 — Psychological Context

Layer 5 is an **overlay**, not a replacement for physical fatigue or injury data:

| Signal | Engine | Effect |
|--------|--------|--------|
| **A — Targeted abuse / morale** | `psychological_engine` → `momentum_engine` | −3% to −5% focus decay on penalties & pressure passing when incident + toxicity spike align |
| **B — Late-night activity** | `psychological_engine` → `fatigue_engine` | Circadian compounding on `cumulative_fatigue` (capped at +8%) when late sessions + elevated base load |

Toggle with `enable_psychological: true/false` on simulate and full-analysis requests.
Demo signals live in `backend/app/services/psychological_engine.py` (swap for live NLP adapters in production).

## Data Providers

Configure in `.env`:

```bash
LIVE_DATA_PROVIDER=api_sports   # mock | api_sports | sportmonks | footystats
API_SPORTS_KEY=your_key
```

| Provider | Tier | Coverage |
|----------|------|----------|
| StatsBomb | Free (open data) | Training Phase 1 |
| API-Sports | Free 100 req/day | Squads, fixtures, injuries |
| Sportmonks | Free limited | Deep squad data |
| FootyStats | Paid | Full xG, PPDA, PDV enrichment |

## Training Pipeline

```bash
# Phase 1: StatsBomb open data (free)
python -m app.training.train_pipeline --phase 1

# Phase 2: + live API augmentation
python -m app.training.train_pipeline --phase 2

# Phase 3: + FootyStats premium
python -m app.training.train_pipeline --phase 3
```

## Environment Variables

See `.env.example` for full list. Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_API_KEY` | demo | Fallback key when header omitted |
| `API_KEYS` | demo,analyst,enterprise | Comma-separated valid keys |
| `ENFORCE_API_KEY` | false | Require valid `X-API-Key` on `/v1/*` |
| `ENFORCE_RATE_LIMIT` | false | Per-IP rate limiting (Redis-backed) |
| `RATE_LIMIT_PER_MINUTE` | 120 | Max requests per IP per minute |
| `ENFORCE_CREDITS` | false | Enable credit deduction on paid endpoints |
| `REDIS_URL` | redis://redis:6379 | Simulation result cache |
| `MC_SIMULATIONS` | 10000 | Max simulations per request |
| `LOG_LEVEL` | INFO | Application log level |

## Useful Commands

```bash
./deploy.sh logs       # Stream container logs
./deploy.sh stop       # Stop all services
./deploy.sh rebuild    # Clean rebuild
./deploy.sh status     # Container status
docker compose --profile test run --rm test   # Run test suite
gcloud builds submit --config=cloudbuild.yaml .   # GCP staging deploy
```
