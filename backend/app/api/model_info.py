from fastapi import APIRouter
from app.data.seed_data import TEAMS
from app.core.config import FEATURE_NAMES, N_FEATURES

router = APIRouter()


def base_score(t: dict) -> float:
    return (
        (t["elo"] / 2100) * 0.40 +
        (t["form"] / 100) * 0.25 +
        ((5 - t["pdv"]) / 5) * 0.20 +
        (t["xg"] / 2.5) * 0.15
    )


@router.get("/architecture")
def model_architecture():
    return {
        "name": "MatchMLP",
        "version": "3.0",
        "framework": "PyTorch 2.3",
        "input_features": N_FEATURES,
        "feature_names": FEATURE_NAMES,
        "layers": [
            {"layer": "Linear", "in": N_FEATURES, "out": 512},
            {"layer": "BatchNorm1d", "features": 512},
            {"layer": "ReLU"},
            {"layer": "Dropout", "p": 0.3},
            {"layer": "Linear", "in": 512, "out": 256},
            {"layer": "BatchNorm1d", "features": 256},
            {"layer": "ReLU"},
            {"layer": "Dropout", "p": 0.3},
            {"layer": "Linear", "in": 256, "out": 128},
            {"layer": "BatchNorm1d", "features": 128},
            {"layer": "ReLU"},
            {"layer": "Dropout", "p": 0.25},
            {"layer": "Linear", "in": 128, "out": 64},
            {"layer": "BatchNorm1d", "features": 64},
            {"layer": "ReLU"},
            {"layer": "Dropout", "p": 0.2},
            {"layer": "Linear", "in": 64, "out": 3},
            {"layer": "Softmax", "dim": 1, "outputs": ["win", "draw", "loss"]},
        ],
        "training": {
            "loss": "CrossEntropyLoss",
            "optimizer": "Adam",
            "lr": 0.001,
            "weight_decay": 0.0001,
            "scheduler": "ReduceLROnPlateau",
            "patience": 5,
            "epochs": 80,
            "batch_size": 128,
        },
        "feature_groups": {
            "structural_v2": FEATURE_NAMES[:19],
            "pdv_srr_injury": FEATURE_NAMES[19:23],
            "v3_fatigue": FEATURE_NAMES[23:26],
            "v3_chemistry": FEATURE_NAMES[26:28],
            "v3_momentum": FEATURE_NAMES[28:31],
            "v3_tactical": FEATURE_NAMES[31:35],
        },
        "intelligence_layers": [
            "fatigue_travel",
            "chemistry_synergy",
            "momentum_clutch",
            "tactical_matchup",
        ],
    }


@router.get("/rankings")
def champion_rankings(limit: int = 16):
    """Model-score-based champion probability rankings."""
    scores = [(t, base_score(t)) for t in TEAMS[:limit]]
    scores.sort(key=lambda x: -x[1])
    max_s = scores[0][1] if scores else 1.0

    return {
        "version": "3.0",
        "method": "composite_model_score",
        "rankings": [
            {
                "rank": i + 1,
                "name": t["name"],
                "flag": t["flag"],
                "elo": t["elo"],
                "pdv": t["pdv"],
                "srr": t["srr"],
                "model_score": round(s, 4),
                "champion_pct": round((s / max_s) * 28 + max(0, 5 - i) * 1.5, 1),
            }
            for i, (t, s) in enumerate(scores)
        ],
    }
