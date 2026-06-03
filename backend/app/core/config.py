from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
    ]
    MODEL_PATH: str = "/app/data/models/match_mlp.pt"
    SCALER_PATH: str = "/app/data/models/scaler.joblib"

    STATSBOMB_DATA_DIR: str = "/app/data/statsbomb"
    TRAINING_DATA_DIR: str = "/app/data/training"

    LIVE_DATA_PROVIDER: str = "mock"
    API_SPORTS_KEY: str = ""
    SPORTMONKS_KEY: str = ""
    FOOTYSTATS_API_KEY: str = "demo"

    FIFA_API_BASE: str = "https://api.fifa.com/api/v3"
    REDIS_URL: str = "redis://redis:6379"
    MC_SIMULATIONS: int = 10_000
    RAPIDFUZZ_THRESHOLD: int = 88

    DEFAULT_API_KEY: str = "demo"
    ENFORCE_CREDITS: bool = False
    LOG_LEVEL: str = "INFO"
    CACHE_TTL_SIMULATION: int = 3600

    class Config:
        env_file = ".env"


settings = Settings()

FEATURE_NAMES_V2 = [
    "elo_diff", "rank_diff", "wc_titles_diff", "form_pts_diff",
    "xg_diff", "xga_diff", "ppda_diff", "deep_comp_diff",
    "shot_acc_diff", "set_piece_diff", "aerial_diff",
    "pdv_diff", "h2h_wins_diff", "confederation_enc",
    "seeding_diff", "wc_apps_diff", "qual_pts_diff",
    "squad_age_diff", "caps_avg_diff", "home_factor",
    "fatigue_travel_diff", "srr_diff", "injury_penalty_diff",
]

FEATURE_NAMES = FEATURE_NAMES_V2 + [
    "cumulative_fatigue_diff",
    "rest_hours_decay_diff",
    "timezone_shift_diff",
    "synergy_multiplier_diff",
    "xt_offensive_compat_diff",
    "clutch_rating_diff",
    "goal_response_delta_diff",
    "penalty_composite_diff",
    "tactical_neutralisation_diff",
    "press_efficacy_delta",
    "high_line_risk_flag",
    "late_game_drop_diff",
]

N_FEATURES = len(FEATURE_NAMES)
N_FEATURES_V2 = len(FEATURE_NAMES_V2)

# Feature index groups for weight application
ELO_INDICES = {0, 1, 2, 14, 15, 16, 17, 18}
FORM_INDICES = {3}
PDV_INDICES = {11}
XG_INDICES = {4, 5, 6, 7, 8, 9, 10}
SRR_INDICES = {21}
V3_FATIGUE_INDICES = {20, 23, 24, 25}
V3_CHEMISTRY_INDICES = {26, 27}
V3_MOMENTUM_INDICES = {28, 29, 30}
V3_TACTICAL_INDICES = {31, 32, 33, 34}

DEFAULT_WEIGHTS = {
    "elo": 0.40,
    "form": 0.25,
    "pdv": 0.20,
    "xg": 0.15,
    "srr": 0.10,
}
