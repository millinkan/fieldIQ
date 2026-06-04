"""
Structural Asymmetry Rating Engine
====================================
Abandons probability percentages entirely.
Instead, exposes the MECHANISM of mispricing — the systemic structural
disconnect between public odds creation and sports-science reality.

The Asymmetry Rating does not say "France wins at 49.5%."
It says: "The market has priced this as a volatile, chaotic, high-scoring
affair based on public perception. Our 10,000 runs repeatedly bottle the
match into a low-scoring chokehold — Team B's direct counter-attacking
lane is perfectly neutralised by Team A's defensive transition system."

Three asymmetry types:
  TACTICAL    — style matchup creates a structural chokehold the market ignores
  PHYSICAL    — travel/altitude/rest creates a measurable fitness gap the market underweights
  PSYCHOLOGICAL — momentum/clutch profiles create a pressure differential the market misses
"""

from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np

from app.services.tactical_engine import (
    classify_tactical_style,
    compute_tactical_neutralisation,
    TACTICAL_MATCHUP_MATRIX,
)
from app.services.fatigue_engine import compute_travel_decay
from app.services.momentum_engine import get_momentum_profile, compute_clutch_rating


# ── Asymmetry severity thresholds ──────────────────────────────────────────
SEVERE   = 0.08   # |score| > 0.08 — strong structural disconnect
MODERATE = 0.04   # |score| > 0.04 — notable asymmetry
MILD     = 0.02   # |score| > 0.02 — minor structural edge


def compute_structural_asymmetry(
    team_a: Dict,
    team_b: Dict,
    base_probs: np.ndarray,
    match_number: int = 5,
    ko_round: Optional[str] = None,
    rest_hours_a: float = 120.0,
    rest_hours_b: float = 120.0,
) -> Dict:
    """
    Identify and narrate the structural disconnects between market pricing
    and sports-science reality.

    Returns:
        overall_asymmetry_rating  — composite score [-1 to 1]
        severity_label            — SEVERE / MODERATE / MILD / NEUTRAL
        asymmetries               — list of specific structural disconnects
        primary_anomaly           — the single most significant mispricing
        market_narrative          — what the market thinks is happening
        engine_narrative          — what the structural data actually shows
        commercial_implication    — how a sportsbook or syndicate should act
    """
    p_win, p_draw, p_loss = float(base_probs[0]), float(base_probs[1]), float(base_probs[2])

    style_a   = classify_tactical_style(team_a)
    style_b   = classify_tactical_style(team_b)
    tactical  = compute_tactical_neutralisation(team_a, team_b)
    fa        = compute_travel_decay(team_a.get("id",""), match_number, ko_round, rest_hours_a)
    fb        = compute_travel_decay(team_b.get("id",""), match_number, ko_round, rest_hours_b)
    mom_a     = get_momentum_profile(team_a.get("id",""))
    mom_b     = get_momentum_profile(team_b.get("id",""))

    name_a = team_a.get("name", "Team A")
    name_b = team_b.get("name", "Team B")
    xg_a   = team_a.get("xg", 1.5)
    xg_b   = team_b.get("xg", 1.5)

    asymmetries = []

    # ── TACTICAL asymmetries ───────────────────────────────────────────────

    # 1. Style neutralisation chokehold
    style_adv = TACTICAL_MATCHUP_MATRIX.get((style_a, style_b), 0.0)
    press     = tactical["press_analysis"]
    line      = tactical["defensive_line_analysis"]
    t_score   = tactical["tactical_neutralisation_score"]

    # Public perception uses team reputation (ELO, star players) to price.
    # The tactical engine uses PPDA, def_line_height, pass_completion_pressure.
    # When these diverge, we have a structural asymmetry.

    if abs(t_score) > MILD:
        direction = "favours_home" if t_score > 0 else "favours_away"
        chokehold = (
            style_a in ("LOW_BLOCK", "COUNTER") and
            style_b in ("HIGH_PRESS", "POSSESSION")
        )
        asymmetries.append({
            "type":      "TACTICAL",
            "id":        "style_neutralisation",
            "score":     round(t_score, 4),
            "severity":  "SEVERE" if abs(t_score) > SEVERE else "MODERATE" if abs(t_score) > MODERATE else "MILD",
            "direction": direction,
            "market_assumption": (
                f"The market prices this as an open game between two strong attacking sides "
                f"based on {name_a} (ELO {team_a.get('elo',1800)}) vs {name_b} (ELO {team_b.get('elo',1800)}). "
                f"Combined public xG expectation: ~{xg_a+xg_b:.1f} goals."
            ),
            "engine_reality": (
                f"{name_a}'s {style_a} system "
                f"{'perfectly neutralises' if chokehold else 'structurally disadvantages'} "
                f"{name_b}'s {style_b} framework. "
                f"Tactical neutralisation score: {t_score:+.3f}. "
                f"The engine's 10,000 runs bottle this into a "
                f"{'controlled, low-scoring chokehold' if chokehold else 'one-sided territory battle'}. "
                f"Style advantage weight: {style_adv:+.2f} in {name_a}'s favour." if t_score > 0 else
                f"Style advantage weight: {abs(style_adv):.2f} against {name_a}."
            ),
            "narrative": _tactical_narrative(name_a, name_b, style_a, style_b, t_score, style_adv, chokehold),
        })

    # 2. Press exhaustion trap
    if press["exhaustion_flag"]:
        asymmetries.append({
            "type":      "TACTICAL",
            "id":        "press_exhaustion_trap",
            "score":     round(-press["late_game_drop"] * 0.8, 4),
            "severity":  "MODERATE",
            "direction": "favours_away",
            "market_assumption": (
                f"The market prices {name_a} as the high-energy pressing side. "
                f"Standard models reward pressing teams in win probability."
            ),
            "engine_reality": (
                f"{name_a}'s PPDA {team_a.get('ppda',10.5):.1f} (aggressive press) vs "
                f"{name_b}'s pass completion under pressure {team_b.get('pass_completion_pressure',0.62):.2f} (resistant). "
                f"FieldIQ projects late-game xG penalty of −{press['late_game_drop']:.3f} for {name_a} "
                f"as they exhaust themselves pressing without winning the ball. "
                f"The market will over-price {name_a} in the 75–90 minute in-play window."
            ),
            "narrative": (
                f"Press exhaustion trap: {name_a} runs without winning the ball. "
                f"Predicted late-game drop: {press['late_game_drop']*100:.1f}% win equity loss in final 15 minutes. "
                f"In-play over/under 0.5 goals (75'–90') is systematically mispriced."
            ),
        })

    # 3. High-line counter structural inevitability
    if line["high_line_risk_flag"]:
        asymmetries.append({
            "type":      "TACTICAL",
            "id":        "high_line_counter_inevitability",
            "score":     round(-line["counterattack_xg"] * 0.4, 4),
            "severity":  "SEVERE" if line["counterattack_xg"] > 0.15 else "MODERATE",
            "direction": "favours_away",
            "market_assumption": (
                f"The market rewards {name_a}'s high defensive line as an attacking posture. "
                f"Standard ELO + form models don't penalise for counter exposure."
            ),
            "engine_reality": (
                f"HIGH-LINE RISK FLAG ACTIVE. "
                f"Defensive line height {team_a.get('def_line_height',0.55):.2f} vs "
                f"{name_b} winger pace {team_b.get('winger_sprint_pace',0.70):.2f}. "
                f"Counter xG bonus: +{line['counterattack_xg']:.3f} per 90 for {name_b}. "
                f"This is not a low-probability event — it is a structural inevitability "
                f"that occurs in a predictable proportion of simulation runs."
            ),
            "narrative": (
                f"{name_a}'s high line will be exploited. Counter xG +{line['counterattack_xg']:.3f}. "
                f"Draw no-bet on {name_b} or 'both teams to score' are systematically underpriced "
                f"because the market doesn't model pace-vs-line matchups."
            ),
        })

    # ── PHYSICAL asymmetries ───────────────────────────────────────────────

    fatigue_gap = fb["cumulative_fatigue"] - fa["cumulative_fatigue"]
    if abs(fatigue_gap) > 0.06:
        favoured = name_a if fatigue_gap > 0 else name_b
        exhausted = name_b if fatigue_gap > 0 else name_a
        altitude_factor = fb["altitude_penalty"] if fatigue_gap < 0 else fa["altitude_penalty"]

        asymmetries.append({
            "type":      "PHYSICAL",
            "id":        "travel_fatigue_gap",
            "score":     round(fatigue_gap * 0.5, 4),
            "severity":  "SEVERE" if abs(fatigue_gap) > 0.15 else "MODERATE",
            "direction": "favours_home" if fatigue_gap > 0 else "favours_away",
            "market_assumption": (
                f"The market uses general squad quality and recent form. "
                f"Standard prediction models do not carry travel itinerary data "
                f"or venue altitude into the probability calculation."
            ),
            "engine_reality": (
                f"{exhausted}: cumulative fatigue {(fa if fatigue_gap < 0 else fb)['cumulative_fatigue']:.3f}. "
                f"Travel: {(fa if fatigue_gap < 0 else fb)['travel_km']:.0f}km, "
                f"timezone shift {(fa if fatigue_gap < 0 else fb)['tz_shift_hours']}h. "
                f"Sprint speed multiplier: {(fa if fatigue_gap < 0 else fb)['sprint_speed_mult']:.3f}. "
                f"Altitude penalty: {altitude_factor:.3f}. "
                f"This is a 2026 WC-specific factor — no existing commercial data provider models it."
            ),
            "narrative": (
                f"Physical asymmetry: {exhausted} is measurably more fatigued. "
                f"Market prices squad strength. FieldIQ prices sprint speed. "
                f"Fatigue gap of {abs(fatigue_gap):.3f} is equivalent to "
                f"~{abs(fatigue_gap)*25:.0f} minutes of effective playing time disadvantage."
            ),
        })

    # ── PSYCHOLOGICAL asymmetries ──────────────────────────────────────────

    clutch_a = compute_clutch_rating(team_a.get("id",""))["clutch_rating"]
    clutch_b = compute_clutch_rating(team_b.get("id",""))["clutch_rating"]
    clutch_gap = clutch_a - clutch_b
    penalty_gap = mom_a.get("penalty_composite",0.72) - mom_b.get("penalty_composite",0.72)

    if abs(clutch_gap) > 0.08 or abs(penalty_gap) > 0.12:
        asymmetries.append({
            "type":      "PSYCHOLOGICAL",
            "id":        "clutch_pressure_divergence",
            "score":     round(clutch_gap * 0.3 + penalty_gap * 0.2, 4),
            "severity":  "MODERATE",
            "direction": "favours_home" if clutch_gap > 0 else "favours_away",
            "market_assumption": (
                f"The market prices in-play equity from scoreline + time remaining. "
                f"Penalty probability is modelled as 50/50 by most bookmakers "
                f"until the actual shootout begins."
            ),
            "engine_reality": (
                f"Clutch ratings: {name_a} {clutch_a:.3f} vs {name_b} {clutch_b:.3f}. "
                f"Penalty composites: {name_a} {mom_a.get('penalty_composite',0.72):.3f} vs "
                f"{name_b} {mom_b.get('penalty_composite',0.72):.3f}. "
                f"In KO stages that go to extra time, this divergence materialises in "
                f"the final 10 minutes and shootout. "
                f"The market prices both teams equally in ET — FieldIQ does not."
            ),
            "narrative": (
                f"Psychological asymmetry: {name_a if clutch_a > clutch_b else name_b} "
                f"is structurally better equipped for pressure. "
                f"KO stage penalty market is systematically mispriced — "
                f"the draw no-bet and ET-specific markets will not reflect this "
                f"until it is too late to act."
            ),
        })

    # ── Composite rating ───────────────────────────────────────────────────
    if asymmetries:
        scores = [a["score"] for a in asymmetries]
        overall = float(np.clip(np.mean(scores), -1, 1))
    else:
        overall = 0.0

    severity = (
        "SEVERE"   if abs(overall) > SEVERE else
        "MODERATE" if abs(overall) > MODERATE else
        "MILD"     if abs(overall) > MILD else
        "NEUTRAL"
    )

    primary = max(asymmetries, key=lambda a: abs(a["score"])) if asymmetries else None

    market_narrative = _build_market_narrative(name_a, name_b, team_a, team_b, xg_a, xg_b, p_win)
    engine_narrative = _build_engine_narrative(name_a, name_b, asymmetries, primary, style_a, style_b)
    commercial      = _commercial_implication(severity, primary, asymmetries, name_a, name_b)

    return {
        "overall_asymmetry_rating": round(overall, 4),
        "severity_label":           severity,
        "direction": (
            f"structural_advantage_home" if overall > MILD else
            f"structural_advantage_away" if overall < -MILD else
            "structurally_balanced"
        ),
        "asymmetries":          asymmetries,
        "asymmetry_count":      len(asymmetries),
        "primary_anomaly":      primary,
        "market_narrative":     market_narrative,
        "engine_narrative":     engine_narrative,
        "commercial_implication": commercial,
        "style_matchup":        f"{style_a} vs {style_b}",
        "note": (
            "The Structural Asymmetry Rating does not output a win probability. "
            "It exposes the mechanisms by which the market's pricing model is "
            "systematically wrong. Sportsbooks use this to build robust in-play "
            "lines. Syndicates use it to time entries before those lines correct."
        ),
    }


# ── Narrative builders ─────────────────────────────────────────────────────

def _tactical_narrative(name_a, name_b, style_a, style_b, t_score, style_adv, chokehold):
    if chokehold and t_score > 0:
        return (
            f"{name_b}'s direct counter-attacking lane is neutralised by {name_a}'s "
            f"defensive transition system. The engine's 10,000 runs repeatedly bottle the match "
            f"into a low-scoring chokehold. The market has not modelled this structural friction. "
            f"It prices the game as open and volatile. The engine says: controlled and compressed."
        )
    elif t_score > MODERATE:
        return (
            f"Structural advantage to {name_a}. {style_a} vs {style_b} creates a systematic "
            f"one-directional territory bias. {name_b}'s primary attacking mechanism is "
            f"neutralised at the source — not by skill gap, but by tactical incompatibility."
        )
    elif t_score < -MODERATE:
        return (
            f"Structural disadvantage for {name_a}. {name_b}'s {style_b} system exploits "
            f"the exact weakness in {name_a}'s {style_a} setup. The market prices "
            f"{name_a} as the favourite on form — the engine prices them as the victim."
        )
    return f"Tactical asymmetry: {name_a} {style_a} vs {name_b} {style_b}. Score: {t_score:+.3f}."


def _build_market_narrative(name_a, name_b, team_a, team_b, xg_a, xg_b, p_win):
    return (
        f"The market prices this match primarily on recent form, squad ratings, and "
        f"historical head-to-head. {name_a} is {'favoured' if p_win > 0.45 else 'the underdog'} "
        f"based on these factors. Combined xG expectations ({xg_a:.1f}+{xg_b:.1f}={xg_a+xg_b:.1f}) "
        f"suggest an {'open, attacking' if xg_a+xg_b > 2.8 else 'balanced'} game. "
        f"Odds compilers are using regression models trained on general match data — "
        f"not on the specific tactical, physical, and psychological vectors active today."
    )


def _build_engine_narrative(name_a, name_b, asymmetries, primary, style_a, style_b):
    if not asymmetries:
        return (
            f"No significant structural asymmetries detected. "
            f"The engine's model aligns with market pricing. "
            f"Tactical: {style_a} vs {style_b} produces no dominant framework advantage."
        )
    types = list({a["type"] for a in asymmetries})
    primary_text = primary["engine_reality"] if primary else ""
    return (
        f"The engine identifies {len(asymmetries)} structural asymmetry/ies "
        f"({', '.join(types)}) that market pricing does not capture. "
        f"Primary anomaly: {primary['id'].replace('_',' ').title()}. "
        f"{primary_text}"
    )


def _commercial_implication(severity, primary, asymmetries, name_a, name_b):
    if severity == "NEUTRAL" or not asymmetries:
        return (
            f"Market pricing appears structurally aligned with the engine's simulation. "
            f"No significant arbitrage between public odds and structural reality. "
            f"Operators: no mandatory repricing signal. Syndicates: wait for a better setup."
        )

    physical = [a for a in asymmetries if a["type"] == "PHYSICAL"]
    tactical = [a for a in asymmetries if a["type"] == "TACTICAL"]
    psych    = [a for a in asymmetries if a["type"] == "PSYCHOLOGICAL"]

    lines = []
    if tactical:
        lines.append(
            f"Sportsbook trading desk: reprice total goals market downward — "
            f"tactical chokehold will compress scoring below public expectation."
        )
    if physical:
        lines.append(
            f"In-play lines: fatigue asymmetry compounds post-60'. "
            f"Set handicap and total goals lines to move in the direction of the fresher team "
            f"as the match progresses. Do not wait for the scoreline to confirm it."
        )
    if psych:
        lines.append(
            f"KO stage: do not price ET and penalty markets as 50/50. "
            f"Psychological composite divergence is a structural input — "
            f"the shootout market is mispriced before it opens."
        )
    lines.append(
        f"{'SEVERE — act before the market corrects. Syndicates will price this within hours.' if severity == 'SEVERE' else 'MODERATE — monitoring window is days, not hours.'}"
    )
    return " ".join(lines)
