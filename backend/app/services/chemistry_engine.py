"""
Layer 2 — In-Game Chemistry & Positional Synergies
====================================================
National teams have ~10 days of training before a tournament.
Club-level chemistry between adjacent position pairs is a real,
measurable competitive edge that traditional stats sites miss entirely.

Features produced:
  synergy_multiplier      — boost from same-club adjacent pairs (0–1 scale)
  xt_offensive_compat     — xT compatibility: winger cross style vs ST aerial
  club_pairs_count        — number of same-club adjacent pairs
  positional_compat_score — overall tactical fit score

References:
  - Pappalardo et al. (2019): "PlayeRank" — positional compatibility in football
  - StatsBomb: xT (Expected Threat) framework
  - Bate (1988): "Football Chance: Tactics and Strategy" — positional adjacency
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple


# Map provider-specific position codes to canonical chemistry codes
POSITION_NORMALIZE: Dict[str, str] = {
    "RB": "FB", "LB": "FB", "RWB": "FB", "LWB": "FB",
    "RW": "W", "LW": "W", "RM": "W", "LM": "W", "WF": "W",
    "CF": "ST", "FW": "ST", "SS": "ST",
    "DM": "CDM", "DMF": "CDM",
    "AM": "CAM", "AMF": "CAM",
    "CMF": "CM", "MF": "CM",
}


def normalize_position(pos: str) -> str:
    pos = (pos or "CM").upper()
    return POSITION_NORMALIZE.get(pos, pos)


def normalize_players(players: List[Dict]) -> List[Dict]:
    return [{**p, "pos": normalize_position(p.get("pos", "CM"))} for p in players]


# ── Adjacent position pairs on the pitch ──────────────────────────────────
# These pairs interact most directly — a chemistry bonus applies when both
# come from the same club.
ADJACENT_PAIRS: List[Tuple[str, str]] = [
    ("GK",  "CB"),   # GK-CB: sweeper-keeper communication
    ("CB",  "CB"),   # CB-CB: defensive partnership
    ("CB",  "FB"),   # CB-FB: wide defensive channel
    ("FB",  "CDM"),  # FB-CDM: press trigger coordination
    ("CDM", "CM"),   # CDM-CM: midfield pivot
    ("CM",  "CM"),   # CM-CM: central midfield pair
    ("CM",  "CAM"),  # CM-CAM: transitional link
    ("CAM", "ST"),   # CAM-ST: final-third combination
    ("CAM", "W"),    # CAM-W: wide attack connection
    ("W",   "ST"),   # W-ST: crossing / aerial combination
    ("FB",  "W"),    # FB-W: overlapping run channel
]

# Chemistry bonus per same-club adjacent pair
CLUB_CHEMISTRY_BONUS = 0.035   # 3.5% per pair, additive up to cap
CLUB_CHEMISTRY_CAP   = 0.18    # max 18% total synergy boost

# How much the synergy multiplier shifts pass_completion and def_compactness
PASS_COMPLETION_WEIGHT  = 0.60
DEF_COMPACTNESS_WEIGHT  = 0.40


def compute_club_chemistry(players: List[Dict]) -> Dict:
    """
    Given a list of player dicts (each with 'pos' and 'club_id'),
    compute the club-level chemistry Synergy_Multiplier.

    Player dict schema:
        pos:     "GK"|"CB"|"FB"|"CDM"|"CM"|"CAM"|"W"|"ST"
        club_id: str — e.g. "real_madrid", "manchester_city"
        rating:  int

    Returns:
        synergy_multiplier:   float [0-1] boost from shared clubs
        club_pairs:           list of (player_a, player_b, club) matched pairs
        pass_completion_adj:  float — adjusted pass completion factor
        def_compactness_adj:  float — adjusted defensive compactness
        dominant_club:        str|None — most represented club in the XI
    """
    pos_to_players: Dict[str, List[Dict]] = {}
    for p in normalize_players(players):
        pos = p.get("pos", "CM")
        pos_to_players.setdefault(pos, []).append(p)

    matched_pairs = []
    bonus_total = 0.0

    for pos_a, pos_b in ADJACENT_PAIRS:
        group_a = pos_to_players.get(pos_a, [])
        group_b = pos_to_players.get(pos_b, [])

        for pa in group_a:
            for pb in group_b:
                if pa is pb:
                    continue
                club_a = pa.get("club_id", "")
                club_b = pb.get("club_id", "")
                if club_a and club_b and club_a == club_b:
                    matched_pairs.append({
                        "player_a": pa.get("name", "?"),
                        "player_b": pb.get("name", "?"),
                        "club":     club_a,
                        "pos_pair": f"{pos_a}-{pos_b}",
                    })
                    bonus_total += CLUB_CHEMISTRY_BONUS

    synergy_multiplier = min(CLUB_CHEMISTRY_CAP, bonus_total)

    # Deduplicate pairs (same pair can match multiple adjacent entries)
    seen = set()
    unique_pairs = []
    for pair in matched_pairs:
        key = tuple(sorted([pair["player_a"], pair["player_b"]]))
        if key not in seen:
            seen.add(key)
            unique_pairs.append(pair)

    synergy_multiplier = min(CLUB_CHEMISTRY_CAP, len(unique_pairs) * CLUB_CHEMISTRY_BONUS)

    # Dominant club
    club_counts: Dict[str, int] = {}
    for p in players:
        c = p.get("club_id", "")
        if c:
            club_counts[c] = club_counts.get(c, 0) + 1
    dominant_club = max(club_counts, key=club_counts.get) if club_counts else None

    pass_adj = 1.0 + synergy_multiplier * PASS_COMPLETION_WEIGHT
    def_adj  = 1.0 + synergy_multiplier * DEF_COMPACTNESS_WEIGHT

    return {
        "synergy_multiplier":   round(synergy_multiplier, 4),
        "club_pairs_count":     len(unique_pairs),
        "club_pairs":           unique_pairs[:10],  # top 10 for API response
        "pass_completion_adj":  round(pass_adj, 4),
        "def_compactness_adj":  round(def_adj, 4),
        "dominant_club":        dominant_club,
    }


# ── xT Offensive Compatibility ─────────────────────────────────────────────

def compute_xt_compatibility(players: List[Dict]) -> Dict:
    """
    Compute xT-based offensive compatibility between wingers and strikers.

    Winger style: measured by crosses_per_90
    Striker style: measured by aerial_duel_win_pct

    High winger crosses + high striker aerial = strong conversion prediction
    High winger crosses + low striker aerial  = wasted delivery
    Low winger crosses  + high striker aerial = underused striker strength
    Low winger crosses  + low striker aerial  = no incompatibility, different threat

    Returns:
        xt_offensive_compat:    float [0-1]
        conversion_rate_boost:  float — predicted boost to offensive efficiency
        style_warnings:         list  — tactical mismatches flagged
    """
    wingers  = [p for p in normalize_players(players) if p.get("pos") in ("W", "RW", "LW")]
    strikers = [p for p in normalize_players(players) if p.get("pos") in ("ST", "CF")]

    if not wingers or not strikers:
        return {
            "xt_offensive_compat":   0.5,
            "conversion_rate_boost": 0.0,
            "style_warnings":        [],
        }

    avg_crosses     = sum(p.get("crosses_per_90", 2.5) for p in wingers) / len(wingers)
    avg_aerial_win  = sum(p.get("aerial_duel_win_pct", 0.50) for p in strikers) / len(strikers)
    avg_dribble_pct = sum(p.get("dribble_success_pct", 0.55) for p in wingers) / len(wingers)

    # Style compatibility matrix
    # Cross-heavy winger + aerial striker = strong match
    # Inverted dribbler winger + aerial striker = mismatch
    cross_aerial_match = avg_crosses * avg_aerial_win  # higher = better

    # Normalise: typical cross_aerial_match range ~0.5–4.0
    xt_compat = min(1.0, cross_aerial_match / 3.5)

    # Conversion rate boost: compatible styles boost xG conversion
    conversion_boost = (xt_compat - 0.5) * 0.12  # ±6% range

    warnings = []
    if avg_crosses > 3.5 and avg_aerial_win < 0.40:
        warnings.append({
            "type":    "crossing_waste",
            "message": "Wingers are crossing frequently but strikers win fewer than 40% of aerial duels",
            "severity": "HIGH",
        })
    if avg_dribble_pct > 0.65 and avg_aerial_win > 0.65:
        warnings.append({
            "type":    "style_mismatch",
            "message": "Inverted dribblers paired with aerial strikers — different threat channels not combining",
            "severity": "MED",
        })
    if avg_crosses < 1.5 and avg_aerial_win > 0.70:
        warnings.append({
            "type":    "underused_aerial",
            "message": "Strong aerial striker but wingers rarely cross — consider fullback overlap runs",
            "severity": "LOW",
        })

    return {
        "xt_offensive_compat":   round(xt_compat, 4),
        "conversion_rate_boost": round(conversion_boost, 4),
        "avg_crosses_per_90":    round(avg_crosses, 2),
        "avg_aerial_win_pct":    round(avg_aerial_win, 3),
        "style_warnings":        warnings,
    }


def compute_synergy_differential(team_a_players: List[Dict], team_b_players: List[Dict]) -> float:
    """
    Returns a single differential synergy feature for the 35-dim feature vector.
    Positive = team_a has better chemistry than team_b.
    """
    chem_a = compute_club_chemistry(team_a_players)
    chem_b = compute_club_chemistry(team_b_players)
    xt_a   = compute_xt_compatibility(team_a_players)
    xt_b   = compute_xt_compatibility(team_b_players)

    score_a = chem_a["synergy_multiplier"] * 0.6 + xt_a["xt_offensive_compat"] * 0.4
    score_b = chem_b["synergy_multiplier"] * 0.6 + xt_b["xt_offensive_compat"] * 0.4
    return round(score_a - score_b, 4)
