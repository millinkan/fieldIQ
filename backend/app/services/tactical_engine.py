"""
Layer 4 — Tactical Style Matchups (The Matrix Layer)
=====================================================
Certain tactical systems naturally neutralise others.
High press vs press-resistant buildup.
High defensive line vs elite-pace wingers.
This engine quantifies those structural matchup advantages.

Features produced:
  press_efficacy_delta         — PPDA advantage after accounting for press resistance
  high_line_risk_flag          — 0/1 flag: high defensive line vs fast wingers
  defensive_block_height_diff  — differential in average defensive line height
  tactical_neutralisation_score — composite matchup advantage [−1 to 1]
  late_game_drop_prediction    — predicted fatigue-driven defensive degradation
                                  when pressing hard against a press-resistant team

Tactical frameworks modelled:
  - High Press  (PPDA < 9)   → strong vs possession teams, weak vs direct play
  - Low Block   (PPDA > 12)  → strong vs high press, weak vs patient build-up
  - High Line   → strong vs slow attacks, catastrophic vs pace on the break
  - Direct Play → beats high press, struggles vs deep blocks
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple


# ── Tactical style classification ─────────────────────────────────────────

def classify_tactical_style(team: Dict) -> str:
    """
    Classify a team's tactical style from their stats.
    Returns one of: HIGH_PRESS | POSSESSION | DIRECT | LOW_BLOCK | COUNTER
    """
    ppda      = team.get("ppda",      10.5)
    deep_comp = team.get("deep_comp", 45.0)
    shot_acc  = team.get("shot_acc",  0.32)
    xg        = team.get("xg",        1.5)
    xga       = team.get("xga",       1.2)

    if ppda < 9.0:
        return "HIGH_PRESS"
    elif ppda < 10.5 and deep_comp > 50:
        return "POSSESSION"
    elif xg < 1.3 and xga < 1.1:
        return "LOW_BLOCK"
    elif xg > 1.8 and ppda > 11:
        return "COUNTER"
    else:
        return "DIRECT"


# ── Tactical matchup advantage matrix ─────────────────────────────────────
# (team_a_style, team_b_style) → advantage multiplier for team_a win prob
# Positive = team_a favoured, negative = team_b favoured, 0 = neutral
TACTICAL_MATCHUP_MATRIX: Dict[Tuple[str, str], float] = {
    ("HIGH_PRESS",  "POSSESSION"):  0.12,   # press disrupts possession play
    ("HIGH_PRESS",  "DIRECT"):     -0.10,   # direct play beats the press with long balls
    ("HIGH_PRESS",  "LOW_BLOCK"):  -0.06,   # hard to break down a low block with press
    ("HIGH_PRESS",  "COUNTER"):    -0.08,   # counter team exploits press gaps
    ("HIGH_PRESS",  "HIGH_PRESS"):  0.00,   # neutral
    ("POSSESSION",  "HIGH_PRESS"):  -0.12,
    ("POSSESSION",  "DIRECT"):      0.06,
    ("POSSESSION",  "LOW_BLOCK"):   0.04,
    ("POSSESSION",  "COUNTER"):    -0.04,
    ("POSSESSION",  "POSSESSION"):  0.00,
    ("DIRECT",      "HIGH_PRESS"):  0.10,
    ("DIRECT",      "POSSESSION"):  -0.06,
    ("DIRECT",      "LOW_BLOCK"):  -0.04,
    ("DIRECT",      "COUNTER"):     0.03,
    ("DIRECT",      "DIRECT"):      0.00,
    ("LOW_BLOCK",   "HIGH_PRESS"):  0.06,
    ("LOW_BLOCK",   "POSSESSION"):  -0.04,
    ("LOW_BLOCK",   "DIRECT"):      0.04,
    ("LOW_BLOCK",   "COUNTER"):    -0.05,
    ("LOW_BLOCK",   "LOW_BLOCK"):   0.00,
    ("COUNTER",     "HIGH_PRESS"):  0.08,
    ("COUNTER",     "POSSESSION"):  0.04,
    ("COUNTER",     "DIRECT"):     -0.03,
    ("COUNTER",     "LOW_BLOCK"):   0.05,
    ("COUNTER",     "COUNTER"):     0.00,
}


def compute_press_efficacy(team_a: Dict, team_b: Dict) -> Dict:
    """
    Compare Team A's pressing intensity (PPDA) against Team B's ability
    to play through the press (Pass_Completion_Under_Pressure).

    If Team B is highly press-resistant:
      → Team A wastes energy pressing without winning the ball
      → Late-game drop prediction triggers for Team A

    Returns press matchup analysis with late_game_drop_prediction.
    """
    ppda_a       = team_a.get("ppda",             10.5)
    ppda_b       = team_b.get("ppda",             10.5)
    press_res_b  = team_b.get("pass_completion_pressure", 0.62)  # Team B's resistance
    press_res_a  = team_a.get("pass_completion_pressure", 0.62)

    # Pressing efficacy: how well does team_a's press work vs team_b?
    # Low PPDA = aggressive press. High press_resistance = it doesn't work.
    press_intensity_a = max(0.0, (12.0 - ppda_a) / 6.0)  # 0=no press, 1=max press
    press_efficacy    = press_intensity_a * (1.0 - press_res_b)

    # Late-game exhaustion: pressing hard against resistant opponent = physical cost
    if press_intensity_a > 0.6 and press_res_b > 0.65:
        late_game_drop = min(0.20, (press_intensity_a * press_res_b - 0.35) * 0.40)
        exhaustion_flag = True
    else:
        late_game_drop = 0.0
        exhaustion_flag = False

    # Press_efficacy_delta: team_a net advantage
    press_delta = press_efficacy - (max(0.0, (12.0 - ppda_b) / 6.0) * (1.0 - press_res_a))

    return {
        "press_intensity_a":     round(press_intensity_a, 3),
        "press_resistance_b":    round(press_res_b, 3),
        "press_efficacy_a":      round(press_efficacy, 3),
        "press_efficacy_delta":  round(press_delta, 3),
        "late_game_drop":        round(late_game_drop, 3),
        "exhaustion_flag":       exhaustion_flag,
        "ppda_a":                ppda_a,
        "ppda_b":                ppda_b,
    }


def compute_defensive_line_risk(team_a: Dict, team_b: Dict) -> Dict:
    """
    Evaluate high defensive line risk.

    If Team A plays a high defensive line AND Team B has wingers/forwards
    with elite sprint acceleration, the "high-risk counterattack" flag fires.

    Features:
        def_line_height:    0-1 scale (1 = very high, 0 = deep block)
        opponent_pace:      0-1 scale (1 = extreme pace)
        high_line_risk_flag: 0/1
        counterattack_xg:   predicted xG Team B gains from counter threat
    """
    def_line_a    = team_a.get("def_line_height",  0.55)  # 0=deep, 1=high
    def_line_b    = team_b.get("def_line_height",  0.55)
    pace_b        = team_b.get("winger_sprint_pace", 0.55)  # normalised sprint speed
    pace_a        = team_a.get("winger_sprint_pace", 0.55)

    # High line risk threshold: line height > 0.65 AND opponent pace > 0.70
    high_line_risk = int(def_line_a > 0.65 and pace_b > 0.70)

    # CounterXG bonus for high-pace team against a high line
    counter_xg_bonus = 0.0
    if high_line_risk:
        counter_xg_bonus = (def_line_a - 0.65) * pace_b * 0.80

    # Reciprocal: does team_b's line expose them to team_a's pace?
    high_line_risk_b   = int(def_line_b > 0.65 and pace_a > 0.70)
    counter_xg_bonus_b = 0.0
    if high_line_risk_b:
        counter_xg_bonus_b = (def_line_b - 0.65) * pace_a * 0.80

    # Net defensive vulnerability differential
    line_risk_delta = counter_xg_bonus_b - counter_xg_bonus  # positive = team_a benefits

    return {
        "def_line_height_a":     def_line_a,
        "def_line_height_b":     def_line_b,
        "winger_pace_b":         pace_b,
        "high_line_risk_flag":   high_line_risk,
        "counterattack_xg":      round(counter_xg_bonus, 3),
        "line_risk_delta":       round(line_risk_delta, 3),
        "flag_warning":          "HIGH-RISK: high defensive line vs elite pace" if high_line_risk else None,
    }


def compute_tactical_neutralisation(team_a: Dict, team_b: Dict) -> Dict:
    """
    Full tactical matchup analysis combining:
      1. Style matchup matrix
      2. Press efficacy vs press resistance
      3. Defensive line height risk
      4. Late-game drop prediction

    Returns a single `tactical_score` differential plus detailed breakdown.
    """
    style_a = classify_tactical_style(team_a)
    style_b = classify_tactical_style(team_b)

    # Style matchup advantage
    style_advantage = TACTICAL_MATCHUP_MATRIX.get((style_a, style_b), 0.0)

    # Press matchup
    press = compute_press_efficacy(team_a, team_b)

    # Defensive line risk
    line  = compute_defensive_line_risk(team_a, team_b)

    # Composite tactical neutralisation score [−1 to 1]
    tactical_score = (
        style_advantage          * 0.40 +
        press["press_efficacy_delta"] * 0.35 +
        line["line_risk_delta"]  * 0.25
    )

    # Late-game drop reduces team_a's effective xG in the 80-90 min window
    late_game_xg_penalty = press["late_game_drop"] * 0.15

    flags = []
    if style_advantage > 0.08:
        flags.append(f"{style_a} tactically favoured vs {style_b}")
    if press["exhaustion_flag"]:
        flags.append(f"Press exhaustion risk: {team_a.get('name','A')} presses hard vs resistant {team_b.get('name','B')}")
    if line["high_line_risk_flag"]:
        flags.append(f"High-line counterattack risk for {team_a.get('name','A')}")

    return {
        "style_a":                       style_a,
        "style_b":                       style_b,
        "style_matchup_advantage":       round(style_advantage, 4),
        "press_analysis":                press,
        "defensive_line_analysis":       line,
        "tactical_neutralisation_score": round(tactical_score, 4),
        "late_game_xg_penalty":          round(late_game_xg_penalty, 4),
        "tactical_flags":                flags,
    }


def compute_tactical_differential(team_a: Dict, team_b: Dict) -> float:
    """
    Returns a single differential tactical feature for the feature vector.
    Positive = team_a has a tactical style advantage.
    """
    result = compute_tactical_neutralisation(team_a, team_b)
    return round(result["tactical_neutralisation_score"], 4)
