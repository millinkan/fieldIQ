"""
Phase 1 — StatsBomb Open Data Pipeline
=======================================
Clones the StatsBomb open-data repo and extracts real match events
to build a training dataset for the MatchMLP.

StatsBomb Open Data covers:
  - La Liga, Premier League, Champions League, Women's Super League, NWSL
  - Full event streams: shots, passes, carries, fouls, cards, pressures
  - Free to use under the StatsBomb Open Data licence

Usage:
    python -m app.data_pipeline.statsbomb_ingest
    # or called from app/training/train_pipeline.py

Output:
    data/training/statsbomb_features.parquet   — 23-dim feature matrix
    data/training/statsbomb_labels.parquet     — match outcome labels (0=home_win,1=draw,2=away_win)
    data/training/pipeline_report.json        — ingest statistics
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
REPO_URL    = "https://github.com/statsbomb/open-data.git"
DATA_ROOT   = Path(os.getenv("STATSBOMB_DATA_DIR", "/app/data/statsbomb"))
MATCHES_DIR = DATA_ROOT / "data" / "matches"
EVENTS_DIR  = DATA_ROOT / "data" / "events"
LINEUPS_DIR = DATA_ROOT / "data" / "lineups"
OUT_DIR     = Path(os.getenv("TRAINING_DATA_DIR", "/app/data/training"))


# ── Competition IDs in StatsBomb Open Data ────────────────────────────────
# See open-data/data/competitions.json for the full list
OPEN_COMPETITIONS = {
    2:  "Premier League",
    11: "La Liga",
    16: "Champions League",
    37: "Women's Super League",
    49: "NWSL",
    72: "Copa del Rey",
    106:"UEFA Euro",
}


def clone_or_pull_repo() -> bool:
    """
    Clone the StatsBomb open-data repo if not present, otherwise git pull.
    Uses --filter=blob:none for a shallow clone (saves ~3 GB of history).
    Returns True if data is available.
    """
    if DATA_ROOT.exists() and (MATCHES_DIR).exists():
        logger.info("StatsBomb repo already present — running git pull...")
        result = subprocess.run(
            ["git", "-C", str(DATA_ROOT), "pull", "--quiet"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info("Repo updated successfully")
        else:
            logger.warning(f"git pull warning: {result.stderr[:200]}")
        return True

    logger.info(f"Cloning StatsBomb open-data to {DATA_ROOT} ...")
    DATA_ROOT.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([
        "git", "clone",
        "--filter=blob:none",   # partial clone — fetch blobs on demand
        "--depth=1",
        REPO_URL,
        str(DATA_ROOT),
    ], capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"Clone failed: {result.stderr}")
        return False

    logger.info("Clone complete")
    return True


def load_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    """Load match list for a competition/season."""
    path = MATCHES_DIR / str(competition_id) / f"{season_id}.json"
    if not path.exists():
        return pd.DataFrame()
    with open(path) as f:
        matches = json.load(f)
    return pd.DataFrame(matches)


def load_events(match_id: int) -> pd.DataFrame:
    """Load full event stream for a match."""
    path = EVENTS_DIR / f"{match_id}.json"
    if not path.exists():
        return pd.DataFrame()
    with open(path) as f:
        events = json.load(f)
    return pd.DataFrame(events)


def load_lineups(match_id: int) -> Dict:
    """Load lineup data for both teams in a match."""
    path = LINEUPS_DIR / f"{match_id}.json"
    if not path.exists():
        return {}
    with open(path) as f:
        lineups = json.load(f)
    return {team["team_id"]: team for team in lineups}


# ── PDV calculation from StatsBomb events ─────────────────────────────────

def compute_pdv_from_events(events: pd.DataFrame, team_id: int) -> float:
    """
    Compute the team's Player Discipline Volatility from live event data.
    StatsBomb events include 'foul_committed', 'bad_behaviour' (cards).

    PDV = (yellows_per_90 × 0.5) + (reds_season × 2.5)
        + (late_foul_rate × 1.8) − (cover_score × 0.9)
    """
    if events.empty:
        return 1.0

    team_events = events[events.get("team", pd.Series()).apply(
        lambda t: t.get("id") == team_id if isinstance(t, dict) else False
    )] if "team" in events.columns else pd.DataFrame()

    if team_events.empty:
        return 1.0

    fouls = team_events[team_events["type"].apply(
        lambda t: t.get("id") == 22 if isinstance(t, dict) else False  # foul_committed type id
    )]
    cards = team_events[team_events["type"].apply(
        lambda t: t.get("id") == 9 if isinstance(t, dict) else False   # bad_behaviour type id
    )]

    total_mins = len(events) / 30.0  # rough minutes proxy
    nineties = max(total_mins / 90.0, 0.01)

    yellows = len(cards[cards.get("bad_behaviour_card", pd.Series()).apply(
        lambda c: "Yellow" in str(c) if c else False
    )])
    reds = len(cards[cards.get("bad_behaviour_card", pd.Series()).apply(
        lambda c: "Red" in str(c) if c else False
    )])

    # Late-game fouls: events after minute 70
    late_fouls = 0
    if not fouls.empty and "minute" in fouls.columns:
        late_fouls = len(fouls[fouls["minute"] >= 70])

    total_fouls = max(len(fouls), 1)
    late_foul_rate = late_fouls / total_fouls
    yellows_per_90 = yellows / nineties
    cover_score = min(1.0, 0.5)  # conservative default; real value from squad depth

    return round(
        (yellows_per_90 * 0.5) + (reds * 2.5) + (late_foul_rate * 1.8) - (cover_score * 0.9),
        3
    )


# ── Feature extraction from a single match ────────────────────────────────

def extract_match_features(match_row: pd.Series, events: pd.DataFrame) -> Optional[Dict]:
    """
    Build the 23-dim differential feature vector from a StatsBomb match.
    Maps StatsBomb fields → FieldIQ feature schema.
    """
    try:
        home_id   = match_row["home_team"]["home_team_id"]
        away_id   = match_row["away_team"]["away_team_id"]
        home_score = int(match_row.get("home_score", 0) or 0)
        away_score = int(match_row.get("away_score", 0) or 0)

        # Match outcome label: 0=home_win, 1=draw, 2=away_win
        if home_score > away_score:   label = 0
        elif home_score == away_score: label = 1
        else:                          label = 2

        if events.empty:
            return None

        def team_events(tid):
            if "team" not in events.columns:
                return pd.DataFrame()
            mask = events["team"].apply(
                lambda t: t.get("id") == tid if isinstance(t, dict) else False
            )
            return events[mask]

        home_ev = team_events(home_id)
        away_ev = team_events(away_id)

        def count_type(ev, type_id):
            if ev.empty or "type" not in ev.columns: return 0
            return int(ev["type"].apply(
                lambda t: t.get("id") == type_id if isinstance(t, dict) else False
            ).sum())

        # StatsBomb event type IDs
        # 16 = shot, 17 = shot_saved, 9 = bad_behaviour, 22 = foul, 21 = pressure
        home_shots   = count_type(home_ev, 16)
        away_shots   = count_type(away_ev, 16)
        home_fouls   = count_type(home_ev, 22)
        away_fouls   = count_type(away_ev, 22)
        home_press   = count_type(home_ev, 21)
        away_press   = count_type(away_ev, 21)

        # xG from StatsBomb shot data
        def extract_xg(ev):
            if ev.empty or "shot" not in ev.columns: return 1.2
            shots = ev[ev["type"].apply(lambda t: t.get("id") == 16 if isinstance(t, dict) else False)]
            if shots.empty: return 0.8
            xg_vals = shots["shot"].apply(
                lambda s: s.get("statsbomb_xg", 0) if isinstance(s, dict) else 0
            )
            return float(xg_vals.sum())

        home_xg = extract_xg(home_ev)
        away_xg = extract_xg(away_ev)

        # Shot accuracy
        def shot_accuracy(ev):
            total = count_type(ev, 16)
            if total == 0: return 0.32
            on_target = ev[ev["type"].apply(lambda t: t.get("id") == 16 if isinstance(t, dict) else False)]
            if on_target.empty: return 0.32
            ot = on_target["shot"].apply(
                lambda s: s.get("outcome", {}).get("name") in ("Goal", "Saved")
                if isinstance(s, dict) else False
            ).sum()
            return float(ot) / max(total, 1)

        home_shot_acc = shot_accuracy(home_ev)
        away_shot_acc = shot_accuracy(away_ev)

        # PPDA proxy: pressures / allowed_passes (lower = more aggressive press)
        home_ppda = max(6.0, 12.0 - home_press / max(len(home_ev), 1) * 100)
        away_ppda = max(6.0, 12.0 - away_press / max(len(away_ev), 1) * 100)

        # PDV from live events
        home_pdv = compute_pdv_from_events(events, home_id)
        away_pdv = compute_pdv_from_events(events, away_id)

        # Build 23-dim differential vector (home - away perspective)
        feat = np.array([
            0.0,                              # 0  elo_diff (not in SB data, zeroed)
            0.0,                              # 1  rank_diff
            0.0,                              # 2  wc_titles_diff
            0.0,                              # 3  form_pts_diff
            home_xg - away_xg,               # 4  xg_diff
            away_xg - home_xg,               # 5  xga_diff (flipped: home concedes less = positive)
            away_ppda - home_ppda,            # 6  ppda_diff (home presses more = positive)
            float(home_shots - away_shots),  # 7  deep_comp_diff (shots proxy)
            home_shot_acc - away_shot_acc,   # 8  shot_acc_diff
            0.0,                              # 9  set_piece_diff
            0.0,                              # 10 aerial_diff
            away_pdv - home_pdv,             # 11 pdv_diff
            0.0,                              # 12 h2h_wins_diff
            0.0,                              # 13 confederation_enc
            0.0,                              # 14 seeding_diff
            0.0,                              # 15 wc_apps_diff
            0.0,                              # 16 qual_pts_diff
            0.0,                              # 17 squad_age_diff
            0.0,                              # 18 caps_avg_diff
            1.0,                              # 19 home_factor (club matches have home advantage)
            0.0,                              # 20 fatigue_travel_diff
            0.0,                              # 21 srr_diff
            0.0,                              # 22 injury_penalty_diff
        ], dtype=np.float32)

        return {"features": feat, "label": label, "match_id": match_row.get("match_id")}

    except Exception as e:
        logger.debug(f"Feature extraction failed for match: {e}")
        return None


# ── Main ingest pipeline ───────────────────────────────────────────────────

def run_statsbomb_ingest(
    max_matches: int = 5000,
    competitions: Optional[List[int]] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Full pipeline: clone repo → iterate matches → extract features → return arrays.

    Returns:
        X: np.ndarray shape (N, 23)
        y: np.ndarray shape (N,)  — 0=win, 1=draw, 2=loss
        report: dict with ingest statistics
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not clone_or_pull_repo():
        raise RuntimeError(
            "Could not clone StatsBomb open-data repo. "
            "Check network access or pre-clone manually:\n"
            f"  git clone --depth=1 {REPO_URL} {DATA_ROOT}"
        )

    comp_ids = competitions or list(OPEN_COMPETITIONS.keys())

    # Discover all available season files
    all_season_paths = []
    for cid in comp_ids:
        comp_dir = MATCHES_DIR / str(cid)
        if comp_dir.exists():
            for season_file in comp_dir.glob("*.json"):
                all_season_paths.append((cid, int(season_file.stem)))

    logger.info(f"Found {len(all_season_paths)} competition-season combinations")

    features_list, labels_list = [], []
    report = {
        "competitions_processed": 0,
        "matches_attempted":      0,
        "matches_successful":     0,
        "matches_skipped":        0,
        "pdv_events_extracted":   0,
    }

    for cid, sid in all_season_paths:
        if len(features_list) >= max_matches:
            break

        matches_df = load_matches(cid, sid)
        if matches_df.empty:
            continue

        report["competitions_processed"] += 1
        logger.info(f"  Processing {OPEN_COMPETITIONS.get(cid, cid)} season {sid} "
                    f"— {len(matches_df)} matches")

        for _, match_row in matches_df.iterrows():
            if len(features_list) >= max_matches:
                break

            report["matches_attempted"] += 1
            mid = match_row.get("match_id")
            if not mid:
                report["matches_skipped"] += 1
                continue

            events = load_events(mid)
            result = extract_match_features(match_row, events)

            if result is None:
                report["matches_skipped"] += 1
                continue

            features_list.append(result["features"])
            labels_list.append(result["label"])
            report["matches_successful"] += 1

            if events is not None and not events.empty:
                report["pdv_events_extracted"] += len(events)

    if not features_list:
        raise ValueError(
            "No features extracted from StatsBomb data. "
            "Check that the repo cloned correctly and event files are present."
        )

    X = np.stack(features_list).astype(np.float32)
    y = np.array(labels_list, dtype=np.int64)

    # Persist to parquet for reuse (skip re-cloning on subsequent runs)
    X_df = pd.DataFrame(X, columns=[f"feat_{i}" for i in range(X.shape[1])])
    X_df.to_parquet(OUT_DIR / "statsbomb_features.parquet", index=False)
    pd.Series(y, name="label").to_frame().to_parquet(OUT_DIR / "statsbomb_labels.parquet", index=False)

    with open(OUT_DIR / "pipeline_report.json", "w") as f:
        json.dump(report, f, indent=2)

    logger.info(
        f"Ingest complete: {report['matches_successful']} matches → "
        f"X shape {X.shape}, class distribution: "
        f"win={int((y==0).sum())}, draw={int((y==1).sum())}, loss={int((y==2).sum())}"
    )
    return X, y, report


def load_cached_features() -> Tuple[np.ndarray, np.ndarray]:
    """Load previously extracted features from parquet cache."""
    X_path = OUT_DIR / "statsbomb_features.parquet"
    y_path = OUT_DIR / "statsbomb_labels.parquet"
    if not X_path.exists() or not y_path.exists():
        raise FileNotFoundError(
            "No cached features found. Run run_statsbomb_ingest() first."
        )
    X = pd.read_parquet(X_path).values.astype(np.float32)
    y = pd.read_parquet(y_path)["label"].values.astype(np.int64)
    return X, y


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    X, y, report = run_statsbomb_ingest(max_matches=3000)
    print(f"\n✅ Done — {len(X)} samples extracted")
    print(json.dumps(report, indent=2))
