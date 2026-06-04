"""
Sensitivity Index Engine
=========================
Computes how the match probability matrix warps under discrete event shocks.
Answers the "What If?" questions that in-play trading desks need to price
live lines robustly during a chaotic World Cup broadcast.

Shock events modelled:
  red_card_home_pre60    — Team A red card before 60th minute
  red_card_home_post60   — Team A red card after 60th minute
  red_card_away_pre60    — Team B red card
  injury_sub_key_player  — Key player forced off (PDV cascade)
  concede_first          — Team A goes 1-0 down (game-state shift)
  score_first            — Team A goes 1-0 up (momentum surge)
  corner_goal            — Set piece from corner converts
  high_press_breaks      — Press lands, opposition cracks (territory shift)

Each shock returns:
  win_equity_delta     — change in home win probability (vs baseline)
  market_expected_move — what the market typically prices for this shock
  engine_expected_move — what FieldIQ calculates given structural factors
  asymmetry            — market_expected_move - engine_expected_move
                         positive = market over-reacts, negative = under-reacts
"""

from __future__ import annotations
import numpy as np
from typing import Dict, List, Optional

from app.services.tactical_engine import (
    classify_tactical_style,
    compute_press_efficacy,
    compute_defensive_line_risk,
)
from app.services.momentum_engine import get_momentum_profile
from app.services.fatigue_engine import compute_travel_decay


# ── Market standard reaction coefficients (from historical odds movement data) ──
# These represent the *average* market repricing for each shock event.
# Source: empirical WC/UCL in-play line movement research.
MARKET_STANDARD_MOVES = {
    "red_card_home_pre60":   -0.224,   # -22.4pp average market drop for home red before 60'
    "red_card_home_post60":  -0.148,   # smaller — less time for opponent to exploit
    "red_card_away_pre60":   +0.198,   # mirror
    "red_card_away_post60":  +0.132,
    "injury_sub_key_player": -0.065,   # market under-prices injury impact on average
    "concede_first":         -0.185,   # game-state shift — massive line move
    "score_first":           +0.210,   # going 1-0 up reprices heavily
    "corner_goal":           +0.140,   # set-piece goal signals different team than xG
    "high_press_breaks":     +0.080,   # press landing as predicted
}


def compute_sensitivity_index(
    team_a: Dict,
    team_b: Dict,
    base_probs: np.ndarray,
    match_number: int = 5,
    ko_round: Optional[str] = None,
    rest_hours_a: float = 120.0,
    rest_hours_b: float = 120.0,
) -> Dict:
    """
    For each shock event, compute FieldIQ's structural estimate of the
    win equity change — then compare it to the market's standard move.

    The gap is the Asymmetry: where the market's in-play pricing will
    be wrong, and by how much.
    """
    p_win, p_draw, p_loss = float(base_probs[0]), float(base_probs[1]), float(base_probs[2])

    style_a  = classify_tactical_style(team_a)
    style_b  = classify_tactical_style(team_b)
    press    = compute_press_efficacy(team_a, team_b)
    line     = compute_defensive_line_risk(team_a, team_b)
    mom_a    = get_momentum_profile(team_a.get("id", ""))
    mom_b    = get_momentum_profile(team_b.get("id", ""))
    fa       = compute_travel_decay(team_a.get("id", ""), match_number, ko_round, rest_hours_a)

    pdv_a    = team_a.get("pdv", 1.0)
    srr_a    = team_a.get("srr", 65) / 100.0
    srr_b    = team_b.get("srr", 65) / 100.0
    xg_a     = team_a.get("xg", 1.5)
    xg_b     = team_b.get("xg", 1.5)
    d_line_a = team_a.get("def_line_height", 0.55)
    depth_a  = srr_a   # bench quality proxy
    grd_a    = mom_a.get("goal_response_delta", 0.10)
    grd_b    = mom_b.get("goal_response_delta", 0.10)
    comeback_a = mom_a.get("comeback_rate", 0.30)
    late_surge = mom_a.get("late_surge", 1.00)

    shocks = []

    # ── 1. Red card Team A before 60' ───────────────────────────────────────
    # FieldIQ adjustment: standard drop × (1 - depth_a) × defensive_shape_factor
    # A team with high SRR and strong defensive shape loses less equity than average
    defensive_depth_factor = 1.0 - (depth_a - 0.60) * 0.8
    engine_red_a_pre60 = -0.224 * max(0.55, defensive_depth_factor)
    market_move = MARKET_STANDARD_MOVES["red_card_home_pre60"]
    asymmetry   = market_move - engine_red_a_pre60

    shocks.append({
        "event":              "red_card_home_pre60",
        "label":              f"Red card — {team_a.get('name','Team A')} before 60'",
        "icon":               "card",
        "win_equity_delta":   round(engine_red_a_pre60, 4),
        "market_move":        round(market_move, 4),
        "asymmetry":          round(asymmetry, 4),
        "asymmetry_direction": "market_over_reacts" if asymmetry > 0.02 else
                               "market_under_reacts" if asymmetry < -0.02 else "aligned",
        "narrative": (
            f"If {team_a.get('name','Team A')} receives a red card before the 60th minute, "
            f"their win equity decays by {abs(engine_red_a_pre60)*100:.1f}%, "
            f"whereas the standard market drop-off is {abs(market_move)*100:.1f}%. "
            f"{'The market over-reacts' if asymmetry > 0.02 else 'The market under-reacts'} "
            f"because it {'ignores' if asymmetry < -0.02 else 'does not fully weight'} "
            f"their bench depth (SRR {team_a.get('srr',65)}) "
            f"and {style_a} defensive compactness when reduced to 10 men."
        ),
    })

    # ── 2. Red card Team A after 60' ────────────────────────────────────────
    # Less time remaining — less equity at stake, but fatigue amplifies the drop
    fatigue_mult = 1.0 + fa["cumulative_fatigue"] * 0.5
    engine_red_a_post60 = -0.148 * fatigue_mult * max(0.60, defensive_depth_factor)

    shocks.append({
        "event":              "red_card_home_post60",
        "label":              f"Red card — {team_a.get('name','Team A')} after 60'",
        "icon":               "card",
        "win_equity_delta":   round(engine_red_a_post60, 4),
        "market_move":        round(MARKET_STANDARD_MOVES["red_card_home_post60"], 4),
        "asymmetry":          round(MARKET_STANDARD_MOVES["red_card_home_post60"] - engine_red_a_post60, 4),
        "asymmetry_direction": (
            "market_over_reacts"  if MARKET_STANDARD_MOVES["red_card_home_post60"] - engine_red_a_post60 > 0.02 else
            "market_under_reacts" if MARKET_STANDARD_MOVES["red_card_home_post60"] - engine_red_a_post60 < -0.02 else "aligned"
        ),
        "narrative": (
            f"Post-60' red card with cumulative fatigue {fa['cumulative_fatigue']:.3f}. "
            f"Fatigue amplifies the 10-men penalty — exhausted defenders cover less ground. "
            f"Engine: {abs(engine_red_a_post60)*100:.1f}% vs market standard {abs(MARKET_STANDARD_MOVES['red_card_home_post60'])*100:.1f}%."
        ),
    })

    # ── 3. Injury sub — key player forced off ───────────────────────────────
    # PDV cascade: depends on the injured player's rating vs their replacement
    # Use the PDV score as a proxy for cascading replacement quality
    key_player_impact = pdv_a * 0.025 + (1 - srr_a) * 0.04
    engine_injury = -max(0.02, key_player_impact)

    shocks.append({
        "event":              "injury_sub_key_player",
        "label":              f"Injury substitution — key {team_a.get('name','Team A')} player",
        "icon":               "injury",
        "win_equity_delta":   round(engine_injury, 4),
        "market_move":        round(MARKET_STANDARD_MOVES["injury_sub_key_player"], 4),
        "asymmetry":          round(MARKET_STANDARD_MOVES["injury_sub_key_player"] - engine_injury, 4),
        "asymmetry_direction": (
            "market_over_reacts"  if MARKET_STANDARD_MOVES["injury_sub_key_player"] - engine_injury > 0.02 else
            "market_under_reacts" if MARKET_STANDARD_MOVES["injury_sub_key_player"] - engine_injury < -0.02 else "aligned"
        ),
        "narrative": (
            f"PDV {pdv_a:.1f} + SRR {team_a.get('srr',65)} determines replacement quality. "
            f"Market applies a uniform −{abs(MARKET_STANDARD_MOVES['injury_sub_key_player'])*100:.1f}% regardless of squad depth. "
            f"FieldIQ engine: −{abs(engine_injury)*100:.1f}% — "
            f"{'less damage than market assumes, SRR bench cover is strong' if engine_injury > MARKET_STANDARD_MOVES['injury_sub_key_player'] else 'more damage than market assumes, bench cover is weak'}."
        ),
    })

    # ── 4. Team A concedes first (game-state shift) ─────────────────────────
    # FieldIQ: applies Goal_Response_Delta — teams that surge after conceding
    # lose less equity than the market's standard concede-first repricing
    grd_modifier = grd_a * 0.8   # positive GRD dampens the equity loss
    engine_concede = MARKET_STANDARD_MOVES["concede_first"] + grd_modifier * 0.15
    engine_concede = min(-0.05, engine_concede)   # still negative — you conceded

    shocks.append({
        "event":              "concede_first",
        "label":              f"{team_a.get('name','Team A')} concedes — goes 1-0 down",
        "icon":               "goal_against",
        "win_equity_delta":   round(engine_concede, 4),
        "market_move":        round(MARKET_STANDARD_MOVES["concede_first"], 4),
        "asymmetry":          round(MARKET_STANDARD_MOVES["concede_first"] - engine_concede, 4),
        "asymmetry_direction": (
            "market_over_reacts"  if MARKET_STANDARD_MOVES["concede_first"] - engine_concede > 0.02 else
            "market_under_reacts" if MARKET_STANDARD_MOVES["concede_first"] - engine_concede < -0.02 else "aligned"
        ),
        "narrative": (
            f"Going 1-0 down: market drops win equity {abs(MARKET_STANDARD_MOVES['concede_first'])*100:.1f}% uniformly. "
            f"FieldIQ applies Goal_Response_Delta {grd_a:+.2f} — "
            f"{team_a.get('name','Team A')} {'surges' if grd_a > 0.15 else 'maintains shape' if grd_a > 0 else 'drops'} "
            f"after conceding. Comeback rate {comeback_a:.0%}. "
            f"Engine equity drop: {abs(engine_concede)*100:.1f}% — "
            f"{'market over-prices the deficit' if engine_concede > MARKET_STANDARD_MOVES['concede_first'] else 'market under-prices it'}."
        ),
    })

    # ── 5. Team A scores first ───────────────────────────────────────────────
    # Late surge + momentum amplifies the 1-0 lead more than market assumes
    surge_modifier = (late_surge - 1.0) * 0.15
    engine_score_first = MARKET_STANDARD_MOVES["score_first"] + surge_modifier

    shocks.append({
        "event":              "score_first",
        "label":              f"{team_a.get('name','Team A')} scores — goes 1-0 up",
        "icon":               "goal_for",
        "win_equity_delta":   round(engine_score_first, 4),
        "market_move":        round(MARKET_STANDARD_MOVES["score_first"], 4),
        "asymmetry":          round(MARKET_STANDARD_MOVES["score_first"] - engine_score_first, 4),
        "asymmetry_direction": (
            "market_over_reacts"  if MARKET_STANDARD_MOVES["score_first"] - engine_score_first > 0.02 else
            "market_under_reacts" if MARKET_STANDARD_MOVES["score_first"] - engine_score_first < -0.02 else "aligned"
        ),
        "narrative": (
            f"Going 1-0 up: late-surge ratio {late_surge:.2f}x amplifies the lead. "
            f"Market: +{MARKET_STANDARD_MOVES['score_first']*100:.1f}%. "
            f"FieldIQ: +{engine_score_first*100:.1f}%. "
            f"{'Market under-prices the lead — team momentum compounds.' if engine_score_first > MARKET_STANDARD_MOVES['score_first'] else 'Market aligned with structural momentum.'}"
        ),
    })

    # ── 6. High-line counter exposure materialises ────────────────────────
    counter_xg_bonus = line.get("counterattack_xg", 0)
    engine_counter = -(counter_xg_bonus * 0.25 + 0.04) if line["high_line_risk_flag"] else -0.04

    shocks.append({
        "event":              "high_line_counter",
        "label":              f"High defensive line — counter-attack materialises",
        "icon":               "counter",
        "win_equity_delta":   round(engine_counter, 4),
        "market_move":        -0.06,
        "asymmetry":          round(-0.06 - engine_counter, 4),
        "asymmetry_direction": (
            "market_under_reacts" if engine_counter < -0.08 else
            "market_over_reacts"  if engine_counter > -0.04 else "aligned"
        ),
        "narrative": (
            f"High defensive line ({d_line_a:.2f}) + opponent pace ({team_b.get('winger_sprint_pace',0.70):.2f}). "
            f"Counter xG bonus: +{counter_xg_bonus:.3f}. "
            f"{'HIGH-RISK FLAG ACTIVE: ' if line['high_line_risk_flag'] else 'Low risk: '}"
            f"Engine projects {abs(engine_counter)*100:.1f}% equity drop when counter materialises. "
            f"Market standard move: −6.0%. Asymmetry: {abs(-0.06 - engine_counter)*100:.1f}pp."
        ),
        "flag_active":       bool(line["high_line_risk_flag"]),
    })

    # ── 7. Press breakthrough ───────────────────────────────────────────────
    press_eff = press["press_efficacy_a"]
    engine_press = MARKET_STANDARD_MOVES["high_press_breaks"] * (0.5 + press_eff)

    shocks.append({
        "event":              "press_breakthrough",
        "label":              "High press lands — territorial dominance established",
        "icon":               "press",
        "win_equity_delta":   round(engine_press, 4),
        "market_move":        round(MARKET_STANDARD_MOVES["high_press_breaks"], 4),
        "asymmetry":          round(MARKET_STANDARD_MOVES["high_press_breaks"] - engine_press, 4),
        "asymmetry_direction": (
            "market_over_reacts"  if MARKET_STANDARD_MOVES["high_press_breaks"] - engine_press > 0.02 else
            "market_under_reacts" if MARKET_STANDARD_MOVES["high_press_breaks"] - engine_press < -0.02 else "aligned"
        ),
        "narrative": (
            f"Press efficacy score: {press_eff:.3f}. "
            f"When the high press lands, equity boost scales with efficacy. "
            f"Engine: +{engine_press*100:.1f}% vs market standard +{MARKET_STANDARD_MOVES['high_press_breaks']*100:.1f}%. "
            f"{'Press resistance flag active — less impact than market assumes.' if press.get('exhaustion_flag') else 'No exhaustion flag — press impact at full strength.'}"
        ),
    })

    # Sort by absolute asymmetry — biggest mispricings first
    shocks.sort(key=lambda s: -abs(s["asymmetry"]))

    return {
        "baseline_win_prob":   round(p_win, 4),
        "baseline_draw_prob":  round(p_draw, 4),
        "baseline_loss_prob":  round(p_loss, 4),
        "shocks":              shocks,
        "biggest_asymmetry":   shocks[0]["event"] if shocks else None,
        "note": (
            "Asymmetry = market_expected_move − engine_expected_move. "
            "Positive asymmetry = market over-reacts to this shock. "
            "Negative = market under-reacts. "
            "These are the live in-play pricing errors a sportsbook trading desk "
            "needs to correct before sharp syndicates exploit them."
        ),
    }
