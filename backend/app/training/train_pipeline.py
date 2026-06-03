"""
Training Pipeline — Three-Phase Bootstrap
==========================================
Orchestrates model training across the three bootstrap phases:

  Phase 1 (FREE): StatsBomb open-data → real match event features
  Phase 2 (LOW-COST): Augment with live API data (API-Sports / Sportmonks free tiers)
  Phase 3 (PREMIUM): Full FootyStats enrichment for production accuracy

The pipeline is additive: each phase stacks on top of the previous one.
You can start training immediately with Phase 1 data (zero cost),
then re-train as you accumulate Phase 2 and Phase 3 data.

Usage:
    # From the backend container or local venv:
    python -m app.training.train_pipeline --phase 1
    python -m app.training.train_pipeline --phase 2   # adds live API data
    python -m app.training.train_pipeline --phase 3   # full premium enrichment

    # Or call from code:
    from app.training.train_pipeline import run_training_pipeline
    run_training_pipeline(phase=1)
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
import torch.nn as nn
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from torch.utils.data import DataLoader, TensorDataset

from app.core.config import settings, N_FEATURES
from app.core.features import pad_features
from app.models.mlp import MatchMLP

logger = logging.getLogger(__name__)

OUT_DIR      = Path(os.getenv("TRAINING_DATA_DIR", "/app/data/training"))
MODEL_DIR    = Path(os.path.dirname(settings.MODEL_PATH))
REPORT_PATH  = OUT_DIR / "training_report.json"


# ── Phase 1: StatsBomb open data ──────────────────────────────────────────

def load_phase1_data() -> Tuple[np.ndarray, np.ndarray]:
    """
    Load or generate Phase 1 training data from StatsBomb open-data.
    Falls back to synthetic data if the repo cannot be cloned
    (e.g., no internet access during container build).
    """
    from app.data_pipeline.statsbomb_ingest import (
        run_statsbomb_ingest, load_cached_features
    )

    # Check for cached features first (saves re-cloning on restarts)
    try:
        X, y = load_cached_features()
        logger.info(f"Phase 1: Loaded {len(X)} cached StatsBomb samples")
        return pad_features(X, N_FEATURES), y
    except FileNotFoundError:
        pass

    # Try live ingest
    try:
        logger.info("Phase 1: Running StatsBomb ingest (this may take a few minutes)...")
        X, y, report = run_statsbomb_ingest(max_matches=4000)
        logger.info(f"Phase 1: Extracted {len(X)} samples from StatsBomb open data")
        logger.info(f"  Matches processed: {report['matches_successful']}")
        logger.info(f"  PDV events:        {report['pdv_events_extracted']:,}")
        return pad_features(X, N_FEATURES), y
    except Exception as e:
        logger.warning(f"Phase 1 StatsBomb ingest failed ({e}). Using synthetic fallback.")
        return _generate_synthetic_data(n_samples=8000, seed=42)


def _generate_synthetic_data(n_samples: int = 8000, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Synthetic fallback — biased toward replicating real match distributions.
    Used when StatsBomb repo is unavailable (air-gapped servers, CI, etc.)
    """
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n_samples, N_FEATURES)).astype(np.float32)

    # Realistic biases across key features:
    #   feat[0] elo_diff:  strongest predictor
    #   feat[4] xg_diff:   second strongest
    #   feat[11] pdv_diff: discipline penalty
    #   feat[21] srr_diff: bench depth
    logit = (X[:, 0] * 0.85 + X[:, 4] * 0.55 - X[:, 11] * 0.35 +
             X[:, 21] * 0.20 + X[:, 3] * 0.25)

    p_win  = 1 / (1 + np.exp(-(logit + 0.25)))
    p_draw = np.clip(0.24 - np.abs(logit) * 0.04, 0.08, 0.32)
    p_loss = np.clip(1 - p_win - p_draw, 0.05, 1.0)

    probs = np.column_stack([p_win, p_draw, p_loss])
    probs = np.clip(probs, 1e-6, 1.0)
    probs /= probs.sum(axis=1, keepdims=True)

    y = np.array([rng.choice(3, p=p) for p in probs], dtype=np.int64)
    logger.info(f"Synthetic data: {n_samples} samples, "
                f"win={int((y==0).sum())}, draw={int((y==1).sum())}, loss={int((y==2).sum())}")
    return X, y


# ── Phase 2: Live API augmentation ────────────────────────────────────────

def augment_with_live_data(X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Phase 2: Enrich feature matrix with data from the live adapter
    (API-Sports free tier or Sportmonks free tier).

    In practice this fills in the ELO/rank/form features (cols 0-3) that
    StatsBomb data doesn't provide, and updates team-level stats for
    the WC 2026 seed teams.

    This function is synchronous — it wraps the async adapter calls.
    """
    import asyncio
    from app.data_pipeline.live_adapters import get_adapter
    from app.data.seed_data import TEAMS

    adapter = get_adapter()
    logger.info(f"Phase 2: Augmenting with {adapter.provider_name} live data...")

    if adapter.provider_name == "mock":
        logger.info("Phase 2: Mock adapter active — skipping live augmentation")
        return X, y

    async def fetch_team_stats():
        results = {}
        for team in TEAMS[:16]:  # top 16 to respect free-tier limits
            try:
                stats = await adapter.get_team_stats(team["id"])
                results[team["id"]] = stats
                await asyncio.sleep(0.5)  # polite rate limiting
            except Exception as e:
                logger.debug(f"Could not fetch stats for {team['id']}: {e}")
        return results

    try:
        loop = asyncio.new_event_loop()
        team_stats = loop.run_until_complete(fetch_team_stats())
        loop.close()
    except Exception as e:
        logger.warning(f"Phase 2 live fetch failed: {e}. Continuing without augmentation.")
        return X, y

    if not team_stats:
        return X, y

    # Generate additional training samples from live stats differentials
    teams_list = list(team_stats.values())
    extra_X, extra_y = [], []

    for i, ta in enumerate(teams_list):
        for j, tb in enumerate(teams_list):
            if i >= j:
                continue
            xg_diff  = float(ta.get("xg", 1.5)) - float(tb.get("xg", 1.5))
            form_diff = (float(ta.get("form", 60)) - float(tb.get("form", 60))) / 30.0
            feat = np.zeros(N_FEATURES, dtype=np.float32)
            feat[3] = form_diff
            feat[4] = xg_diff
            extra_X.append(feat)
            label = 0 if xg_diff > 0.15 else (2 if xg_diff < -0.15 else 1)
            extra_y.append(label)

    if extra_X:
        X_aug = np.vstack([X, np.array(extra_X, dtype=np.float32)])
        y_aug = np.concatenate([y, np.array(extra_y, dtype=np.int64)])
        logger.info(f"Phase 2: Added {len(extra_X)} live-derived training samples. "
                    f"Total: {len(X_aug)}")
        return X_aug, y_aug

    return X, y


# ── Phase 3: Premium enrichment ───────────────────────────────────────────

def enrich_with_premium_data(X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Phase 3: Full FootyStats enrichment.
    Fills ALL 23 features with real FootyStats values — xG, xGA, PPDA,
    deep completions, shot accuracy, PDV cascade, SRR — for every team.

    Only runs when FOOTYSTATS_API_KEY is set to a real key.
    Until then this is a no-op that logs a clear upgrade message.
    """
    import asyncio
    from app.data_pipeline.live_adapters import get_adapter, FootyStatsAdapter

    adapter = get_adapter()
    if not isinstance(adapter, FootyStatsAdapter):
        logger.info(
            "Phase 3: FootyStats premium enrichment is inactive.\n"
            "  → Set FOOTYSTATS_API_KEY in .env to enable full feature coverage.\n"
            "  → See https://footystats.org/api for pricing."
        )
        return X, y

    logger.info("Phase 3: Running FootyStats premium enrichment...")
    from app.data.seed_data import TEAMS

    async def fetch_all():
        results = {}
        for team in TEAMS:
            try:
                stats = await adapter.get_team_stats(team["id"])
                squad = await adapter.get_squad(team["id"])
                results[team["id"]] = {**stats, "squad": squad.get("players", [])}
            except Exception as e:
                logger.debug(f"FootyStats fetch failed for {team['id']}: {e}")
        return results

    loop = asyncio.new_event_loop()
    enriched = loop.run_until_complete(fetch_all())
    loop.close()

    if not enriched:
        return X, y

    teams_list = [t for t in TEAMS if t["id"] in enriched]
    extra_X, extra_y = [], []

    for i, ta_seed in enumerate(teams_list):
        for j, tb_seed in enumerate(teams_list):
            if i >= j:
                continue
            ta = {**ta_seed, **enriched.get(ta_seed["id"], {})}
            tb = {**tb_seed, **enriched.get(tb_seed["id"], {})}

            from app.services.prediction import build_feature_vector
            feat = build_feature_vector(ta, tb)
            extra_X.append(feat)

            xg_a = float(ta.get("xg", 1.5))
            xg_b = float(tb.get("xg", 1.5))
            extra_y.append(0 if xg_a > xg_b + 0.1 else (2 if xg_b > xg_a + 0.1 else 1))

    if extra_X:
        X_final = np.vstack([X, np.array(extra_X)])
        y_final = np.concatenate([y, np.array(extra_y)])
        logger.info(f"Phase 3: Added {len(extra_X)} FootyStats samples. Total: {len(X_final)}")
        return X_final, y_final

    return X, y


# ── Core training loop ─────────────────────────────────────────────────────

def train_mlp(
    X: np.ndarray,
    y: np.ndarray,
    epochs: int = 80,
    batch_size: int = 128,
    lr: float = 1e-3,
) -> Tuple[MatchMLP, StandardScaler, Dict]:
    """
    Train the MatchMLP on the final feature matrix.
    Returns model, scaler, and a training metrics report.
    """
    # 80 / 10 / 10 split — no leakage
    X_tr, X_tmp, y_tr, y_tmp = train_test_split(X, y, test_size=0.20, stratify=y, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_tmp, y_tmp, test_size=0.50, stratify=y_tmp, random_state=42)

    scaler = StandardScaler()
    X_tr_s   = scaler.fit_transform(X_tr)
    X_val_s  = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    tr_loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_tr_s), torch.LongTensor(y_tr)),
        batch_size=batch_size, shuffle=True, num_workers=0,
    )

    model     = MatchMLP()
    optimiser = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimiser, patience=6, factor=0.5, verbose=False
    )
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_state    = None
    history       = []

    logger.info(f"Training: {len(X_tr)} train / {len(X_val)} val / {len(X_test)} test")

    for epoch in range(epochs):
        model.train()
        ep_loss = 0.0
        for xb, yb in tr_loader:
            optimiser.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
            ep_loss += loss.item()

        model.eval()
        with torch.no_grad():
            val_logits = model(torch.FloatTensor(X_val_s))
            val_loss   = criterion(val_logits, torch.LongTensor(y_val)).item()
            val_acc    = accuracy_score(y_val, val_logits.argmax(1).numpy())

        scheduler.step(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state    = {k: v.clone() for k, v in model.state_dict().items()}

        if epoch % 10 == 0 or epoch == epochs - 1:
            avg_tr = ep_loss / len(tr_loader)
            logger.info(f"  epoch {epoch:3d} | train {avg_tr:.4f} | val {val_loss:.4f} | val_acc {val_acc:.3f}")
            history.append({"epoch": epoch, "train_loss": round(avg_tr, 4),
                            "val_loss": round(val_loss, 4), "val_acc": round(val_acc, 3)})

    # Restore best checkpoint
    if best_state:
        model.load_state_dict(best_state)

    # Final test evaluation
    model.eval()
    with torch.no_grad():
        test_preds = model(torch.FloatTensor(X_test_s)).argmax(1).numpy()

    test_acc    = accuracy_score(y_test, test_preds)
    test_report = classification_report(
        y_test, test_preds,
        target_names=["win", "draw", "loss"],
        output_dict=True,
    )

    logger.info(f"\nFinal test accuracy: {test_acc:.3f}")
    logger.info(f"Class report:\n{classification_report(y_test, test_preds, target_names=['win','draw','loss'])}")

    metrics = {
        "test_accuracy":    round(test_acc, 4),
        "best_val_loss":    round(best_val_loss, 4),
        "class_report":     test_report,
        "train_samples":    len(X_tr),
        "val_samples":      len(X_val),
        "test_samples":     len(X_test),
        "epochs":           epochs,
        "training_history": history,
    }
    return model, scaler, metrics


# ── Master pipeline entry point ────────────────────────────────────────────

def run_training_pipeline(phase: int = 1, force_retrain: bool = False) -> Dict:
    """
    Run the full training pipeline for the given phase.
    """
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if not force_retrain and settings.MODEL_PATH and Path(settings.MODEL_PATH).exists():
        if REPORT_PATH.exists():
            with open(REPORT_PATH) as f:
                existing = json.load(f)
            if existing.get("phase", 0) >= phase:
                logger.info("Skipping training — model at phase %s already exists (use force=True)", phase)
                return existing

    logger.info(f"\n{'='*60}")
    logger.info(f"FieldIQ Training Pipeline — Phase {phase}")
    logger.info(f"{'='*60}\n")

    # ── Phase 1: StatsBomb ─────────────────────────────────────────
    logger.info("── Phase 1: Loading StatsBomb open data")
    X, y = load_phase1_data()
    data_sources = ["statsbomb_open_data"]

    # ── Phase 2: Live API augmentation ────────────────────────────
    if phase >= 2:
        logger.info("\n── Phase 2: Live API augmentation")
        X, y = augment_with_live_data(X, y)
        data_sources.append(os.getenv("LIVE_DATA_PROVIDER", "mock"))

    # ── Phase 3: Premium enrichment ────────────────────────────────
    if phase >= 3:
        logger.info("\n── Phase 3: Premium FootyStats enrichment")
        X, y = enrich_with_premium_data(X, y)
        data_sources.append("footystats_premium")

    # ── Train ──────────────────────────────────────────────────────
    logger.info(f"\n── Training MatchMLP on {len(X)} samples, {N_FEATURES} features")
    model, scaler, metrics = train_mlp(X, y)

    # ── Save ───────────────────────────────────────────────────────
    torch.save(model.state_dict(), settings.MODEL_PATH)
    joblib.dump(scaler, settings.SCALER_PATH)

    elapsed = round(time.time() - t0, 1)
    report = {
        "phase":          phase,
        "data_sources":   data_sources,
        "total_samples":  len(X),
        "elapsed_sec":    elapsed,
        "model_path":     str(settings.MODEL_PATH),
        **metrics,
    }

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n✅ Phase {phase} training complete in {elapsed}s")
    logger.info(f"   Test accuracy: {metrics['test_accuracy']}")
    logger.info(f"   Model saved:   {settings.MODEL_PATH}")
    logger.info(f"   Report saved:  {REPORT_PATH}")

    # Reload model into the live prediction engine
    from app.core import model_init
    model_init._model  = model
    model_init._scaler = scaler
    logger.info("   Live model reloaded ✓")

    return report


# ── CLI entrypoint ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="FieldIQ Training Pipeline")
    parser.add_argument(
        "--phase", type=int, default=1, choices=[1, 2, 3],
        help="Bootstrap phase: 1=StatsBomb, 2=+LiveAPI, 3=+FootyStats"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-training even if saved weights exist"
    )
    args = parser.parse_args()
    report = run_training_pipeline(phase=args.phase, force_retrain=args.force)
    print(json.dumps({k: v for k, v in report.items() if k != "class_report"}, indent=2))
