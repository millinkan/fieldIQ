"""
Training management API.
Exposes endpoints to trigger retraining, check data source status,
and read the latest training report — all from the FieldIQ dashboard.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import json
import os
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.data_pipeline.live_adapters import get_adapter

router = APIRouter()
logger = logging.getLogger(__name__)

REPORT_PATH = Path(os.getenv("TRAINING_DATA_DIR", "/app/data/training")) / "training_report.json"
_training_in_progress = False


class TrainRequest(BaseModel):
    phase: int = 1          # 1 = StatsBomb, 2 = +LiveAPI, 3 = +FootyStats
    force: bool = False


def _run_training_task(phase: int, force: bool):
    """Background task — runs in a thread pool via FastAPI BackgroundTasks."""
    global _training_in_progress
    _training_in_progress = True
    try:
        from app.training.train_pipeline import run_training_pipeline
        report = run_training_pipeline(phase=phase, force_retrain=force)
        logger.info(f"Training complete — phase={phase}, accuracy={report.get('test_accuracy')}")
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
    finally:
        _training_in_progress = False


@router.post("/train")
def trigger_training(req: TrainRequest, background_tasks: BackgroundTasks):
    """
    Trigger model retraining in the background.

    phase=1: StatsBomb open data (free, ~4000 real matches)
    phase=2: + live API augmentation (API-Sports / Sportmonks free tier)
    phase=3: + FootyStats premium enrichment (requires paid API key)

    Training runs asynchronously. Poll GET /v1/model/train/status for progress.
    """
    global _training_in_progress

    if _training_in_progress:
        raise HTTPException(status_code=409, detail="Training already in progress")

    if req.phase not in (1, 2, 3):
        raise HTTPException(status_code=422, detail="phase must be 1, 2, or 3")

    background_tasks.add_task(_run_training_task, req.phase, req.force)
    _training_in_progress = True

    phase_desc = {
        1: "StatsBomb open data (~4,000 free matches)",
        2: "StatsBomb + live API augmentation (API-Sports/Sportmonks free tier)",
        3: "Full enrichment: StatsBomb + live API + FootyStats premium",
    }

    return {
        "status":      "training_started",
        "phase":       req.phase,
        "description": phase_desc[req.phase],
        "message":     "Training running in background. Poll /v1/model/train/status for progress.",
    }


@router.get("/train/status")
def training_status():
    """Check whether training is currently running and read the last report."""
    report = None
    if REPORT_PATH.exists():
        with open(REPORT_PATH) as f:
            try:
                report = json.load(f)
            except json.JSONDecodeError:
                pass

    return {
        "in_progress": _training_in_progress,
        "last_report": report,
    }


@router.get("/data-sources")
async def data_source_status():
    """
    Show the status of all three data sources and the active provider.
    """
    adapter = get_adapter()
    adapter_status = adapter.status()

    statsbomb_cache = Path(os.getenv("TRAINING_DATA_DIR", "/app/data/training"))
    statsbomb_ready = (statsbomb_cache / "statsbomb_features.parquet").exists()
    statsbomb_repo  = Path(os.getenv("STATSBOMB_DATA_DIR", "/app/data/statsbomb")).exists()

    footystats_key = os.getenv("FOOTYSTATS_API_KEY", "demo")
    api_sports_key = os.getenv("API_SPORTS_KEY", "")
    sportmonks_key = os.getenv("SPORTMONKS_KEY", "")

    return {
        "phases": {
            "phase_1_statsbomb": {
                "name":        "StatsBomb Open Data",
                "cost":        "FREE",
                "repo_cloned": statsbomb_repo,
                "cache_ready": statsbomb_ready,
                "action":      "POST /v1/model/train {phase: 1}",
                "repo_url":    "https://github.com/statsbomb/open-data",
                "coverage":    "La Liga, PL, UCL, WSL — real xG, pressures, fouls, cards",
            },
            "phase_2_live_api": {
                "name":     "Live API (API-Sports / Sportmonks)",
                "cost":     "FREE tier available",
                "provider": os.getenv("LIVE_DATA_PROVIDER", "mock"),
                "status":   adapter_status,
                "api_sports_configured":  bool(api_sports_key),
                "sportmonks_configured":  bool(sportmonks_key),
                "action":   "Set API_SPORTS_KEY or SPORTMONKS_KEY in .env, then POST /v1/model/train {phase: 2}",
                "signup": {
                    "api_sports":  "https://api-sports.io (100 req/day free)",
                    "sportmonks":  "https://sportmonks.com (free plan)",
                },
            },
            "phase_3_premium": {
                "name":       "FootyStats Premium",
                "cost":       "Paid — activate after B2B contracts",
                "configured": footystats_key not in ("demo", "", None),
                "action":     "Set FOOTYSTATS_API_KEY in .env, then POST /v1/model/train {phase: 3}",
                "signup":     "https://footystats.org/api",
                "features":   "Full xG, xGA, PPDA, deep completions, shot maps, PDV enrichment",
            },
        },
        "active_provider": os.getenv("LIVE_DATA_PROVIDER", "mock"),
        "model_weights_exist": os.path.exists(settings.MODEL_PATH),
    }


@router.get("/fixtures")
async def get_upcoming_fixtures(competition_id: int = 1):
    """Fetch upcoming fixtures from the active live data provider."""
    adapter = get_adapter()
    try:
        fixtures = await adapter.get_fixtures(competition_id)
        return {
            "provider":   adapter.provider_name,
            "competition_id": competition_id,
            "fixtures":   fixtures,
            "count":      len(fixtures),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Data provider error: {str(e)}")


@router.get("/injuries/{team_id}")
async def get_live_injuries(team_id: str):
    """Fetch current injury list from the active live data provider."""
    adapter = get_adapter()
    try:
        injuries = await adapter.get_live_injuries(team_id)
        return {
            "provider": adapter.provider_name,
            "team_id":  team_id,
            "injuries": injuries,
            "count":    len(injuries),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Data provider error: {str(e)}")
