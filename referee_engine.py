"""
Layer 6 — Referee Variance Engine
=====================================
FIFA appointed 52 referees from 6 confederations for WC 2026.
Match assignments are published ~48hrs before kickoff.

No public sportsbook model prices referee confederation bias.
Historical WC data shows significant variance by confederation:
  - CONMEBOL refs: 2.1x penalty rate vs UEFA baseline
  - CAF refs: +15% yellow cards/match vs UEFA baseline
  - AFC refs: lowest card rate (most permissive)
  - CONCACAF refs: neutral on cards, elevated penalty rate in high-pressure matches
  - UEFA refs: baseline — most consistent

This engine multiplies your PDV cascade risk by referee tendency,
producing per-match penalty probability and cards market edges.

Features produced:
  ref_cards_multiplier     — expected yellow card rate vs baseline
  ref_penalty_multiplier   — expected penalty rate vs baseline
  pdv_cascade_adjusted     — team PDV score adjusted for referee tendency
  penalty_probability      — match probability of at least 1 penalty (0–1)
  cards_market_edge        — edge vs market "both teams to have a card" (−1 to +1)
  ref_narrative            — human-readable referee impact description
"""

from __future__ import annotations
import math
from typing import Dict, Optional

# ── Referee confederation historical stats (WC 2018 + 2022 baseline) ──────
# Source: WorldReferee.com historical data + academic analysis
# yellows_per_match: average at this confederation's officials
# penalties_per_match: average penalties awarded per match
# fouls_per_match: average fouls called
# reds_per_match: average red cards
REFEREE_CONFEDERATION_STATS: Dict[str, Dict] = {
    "UEFA": {
        "yellows_per_match":   3.8,
        "penalties_per_match": 0.42,
        "fouls_per_match":     22.1,
        "reds_per_match":      0.18,
        "cards_multiplier":    1.00,   # baseline
        "penalty_multiplier":  1.00,
        "description":         "UEFA — baseline, most consistent",
    },
    "CONMEBOL": {
        "yellows_per_match":   4.6,
        "penalties_per_match": 0.88,   # 2.1x UEFA
        "fouls_per_match":     26.4,
        "reds_per_match":      0.24,
        "cards_multiplier":    1.21,
        "penalty_multiplier":  2.10,
        "description":         "CONMEBOL — highest penalty rate, physical game tolerance",
    },
    "CAF": {
        "yellows_per_match":   4.4,
        "penalties_per_match": 0.51,
        "fouls_per_match":     24.8,
        "reds_per_match":      0.22,
        "cards_multiplier":    1.16,
        "penalty_multiplier":  1.21,
        "description":         "CAF — elevated yellow cards, stricter on physicality",
    },
    "AFC": {
        "yellows_per_match":   3.2,
        "penalties_per_match": 0.38,
        "fouls_per_match":     20.4,
        "reds_per_match":      0.14,
        "cards_multiplier":    0.84,
        "penalty_multiplier":  0.90,
        "description":         "AFC — most permissive, lowest card rate",
    },
    "CONCACAF": {
        "yellows_per_match":   3.9,
        "penalties_per_match": 0.52,
        "fouls_per_match":     22.8,
        "reds_per_match":      0.19,
        "cards_multiplier":    1.03,
        "penalty_multiplier":  1.24,
        "description":         "CONCACAF — near-baseline cards, elevated penalties in KO pressure",
    },
    "OFC": {
        "yellows_per_match":   3.6,
        "penalties_per_match": 0.40,
        "fouls_per_match":     21.2,
        "reds_per_match":      0.16,
        "cards_multiplier":    0.95,
        "penalty_multiplier":  0.95,
        "description":         "OFC — similar to AFC, limited WC data",
    },
    "UNKNOWN": {
        "yellows_per_match":   3.8,
        "penalties_per_match": 0.42,
        "fouls_per_match":     22.1,
        "reds_per_match":      0.18,
        "cards_multiplier":    1.00,
        "penalty_multiplier":  1.00,
        "description":         "Unknown — using UEFA baseline",
    },
}

# ── Known WC 2026 referee confederation assignments ───────────────────────
# Source: WorldReferee.com April 2026 announcement
# Only top referees listed; full list updated via scrape 48hrs before match
KNOWN_REFS: Dict[str, str] = {
    "Szymon Marciniak":    "UEFA",    # Poland — 2022 WC Final referee
    "Ismail Elfath":       "CONCACAF", # USA — experienced WC ref
    "Facundo Tello":       "CONMEBOL", # Argentina
    "Mustapha Ghorbal":    "CAF",      # Algeria
    "Abdulrahman Al-Jassim": "AFC",    # Qatar
    "Felix Zwayer":        "UEFA",    # Germany
    "Clement Turpin":      "UEFA",    # France
    "Danny Makkelie":      "UEFA",    # Netherlands
    "Anthony Taylor":      "UEFA",    # England
    "Michael Oliver":      "UEFA",    # England
    "Slavko Vincic":       "UEFA",    # Slovenia
    "Ivan Barton":         "CONCACAF", # El Salvador
    "Janny Sikazwe":       "CAF",      # Zambia
    "Ma Ning":             "AFC",      # China
    "Wilton Sampaio":      "CONMEBOL", # Brazil
}


def get_referee_profile(ref_name: Optional[str] = None,
                        ref_confederation: Optional[str] = None) -> Dict:
    """
    Get referee statistical profile.
    Accepts either a known referee name OR a confederation directly.
    If neither provided, returns UEFA baseline.
    """
    if ref_confederation and ref_confederation in REFEREE_CONFEDERATION_STATS:
        conf = ref_confederation
    elif ref_name and ref_name in KNOWN_REFS:
        conf = KNOWN_REFS[ref_name]
    else:
        conf = "UNKNOWN"

    return {
        "confederation": conf,
        **REFEREE_CONFEDERATION_STATS[conf],
    }


def compute_referee_impact(
    home_id: str,
    away_id: str,
    home_pdv: float,
    away_pdv: float,
    home_srr: int,
    away_srr: int,
    ref_name: Optional[str] = None,
    ref_confederation: Optional[str] = None,
    ko_round: Optional[str] = None,
) -> Dict:
    """
    Compute referee impact on match outcome probabilities.

    Key insight: referee tendency interacts with team PDV (disciplinary volatility).
    A physical team with PDV=2.1 under a CONMEBOL ref is VERY different from
    the same team under an AFC ref.

    The penalty market sits at ~+350 (22% implied) for most group games.
    Your model can identify matches where it should be 30-40%.
    """
    ref = get_referee_profile(ref_name, ref_confederation)

    # ── PDV cascade adjustment ─────────────────────────────────────────────
    # Base suspension probability: PDV × 0.12 per KO round (from prediction.py)
    # Referee multiplier adjusts the effective PDV
    ko_mult = 1.0
    if ko_round:
        ko_map = {
            "Round of 32": 1.0, "Round of 16": 1.5,
            "Quarter-finals": 2.0, "Semi-finals": 2.5, "Final": 3.0
        }
        ko_mult = ko_map.get(ko_round, 1.0)

    home_pdv_adjusted = home_pdv * ref["cards_multiplier"]
    away_pdv_adjusted = away_pdv * ref["cards_multiplier"]

    home_susp_prob = min(0.85, home_pdv_adjusted * 0.12 * ko_mult)
    away_susp_prob = min(0.85, away_pdv_adjusted * 0.12 * ko_mult)

    # ── Penalty probability ────────────────────────────────────────────────
    # Base penalty probability per match ≈ 0.42 (UEFA baseline)
    # Physical teams raise this; referee tendency multiplies it
    combined_pdv = (home_pdv + away_pdv) / 2
    base_penalty_prob = 0.35 + combined_pdv * 0.04
    penalty_prob = min(0.85, base_penalty_prob * ref["penalty_multiplier"])

    # Both teams to score a penalty (rarer — compound probability)
    both_penalty_prob = penalty_prob * 0.35  # conditional on first penalty

    # ── Cards market edge ──────────────────────────────────────────────────
    # "Both teams to have a card" market baseline ≈ 55% (priced at ~-120 to -140)
    # "Over 4.5 cards" baseline ≈ 48%
    expected_yellows = ref["yellows_per_match"] * (0.8 + combined_pdv * 0.1)
    both_teams_carded_prob = min(0.95, 0.55 + (expected_yellows - 3.8) * 0.05)

    # ── SRR interaction ────────────────────────────────────────────────────
    # Deep squad (high SRR) is less impacted by suspension risk
    # because backup quality is maintained
    home_suspension_impact = home_susp_prob * (1.0 - home_srr / 200)
    away_suspension_impact = away_susp_prob * (1.0 - away_srr / 200)
    suspension_delta = away_suspension_impact - home_suspension_impact

    # ── Outcome probability adjustment ────────────────────────────────────
    # Referee tendency shifts probabilities when PDV is asymmetric
    pdv_asymmetry = abs(home_pdv - away_pdv)
    if pdv_asymmetry > 0.5 and ref["cards_multiplier"] > 1.1:
        # Physical team vs disciplined team under card-heavy ref
        # Disciplined team gets structural advantage
        disciplined_team = "home" if home_pdv < away_pdv else "away"
        prob_shift = min(0.06, pdv_asymmetry * ref["cards_multiplier"] * 0.02)
    else:
        disciplined_team = "neutral"
        prob_shift = 0.0

    # ── Narrative ──────────────────────────────────────────────────────────
    narratives = []
    if ref["penalty_multiplier"] > 1.5:
        narratives.append(
            f"{ref['confederation']} referee: penalty probability {penalty_prob*100:.0f}% "
            f"(market baseline ~35%). Physical play likely rewarded."
        )
    if ref["cards_multiplier"] > 1.1 and combined_pdv > 1.5:
        narratives.append(
            f"High PDV teams ({home_id}={home_pdv}, {away_id}={away_pdv}) "
            f"+ {ref['confederation']} ref = suspension cascade risk elevated."
        )
    if home_susp_prob > 0.30 or away_susp_prob > 0.30:
        high_risk = home_id if home_susp_prob > away_susp_prob else away_id
        narratives.append(
            f"{high_risk} suspension risk: {max(home_susp_prob, away_susp_prob)*100:.0f}% "
            f"chance of key player yellow/red this match."
        )
    if not narratives:
        narratives.append(f"{ref['confederation']} referee — near-baseline impact expected.")

    return {
        "referee_confederation":   ref["confederation"],
        "ref_description":         ref["description"],
        "cards_multiplier":        ref["cards_multiplier"],
        "penalty_multiplier":      ref["penalty_multiplier"],
        "expected_yellows":        round(expected_yellows, 2),
        "penalty_probability":     round(penalty_prob, 4),
        "both_penalty_probability": round(both_penalty_prob, 4),
        "both_teams_carded_prob":  round(both_teams_carded_prob, 4),
        "home_suspension_prob":    round(home_susp_prob, 4),
        "away_suspension_prob":    round(away_susp_prob, 4),
        "suspension_delta":        round(suspension_delta, 4),
        "disciplined_team_edge":   disciplined_team,
        "prob_shift":              round(prob_shift, 4),
        "cards_market_edge":       round(both_teams_carded_prob - 0.55, 4),
        "penalty_market_edge":     round(penalty_prob - 0.35, 4),
        "narrative":               " ".join(narratives),
    }
