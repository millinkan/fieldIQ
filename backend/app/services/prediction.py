"""Core prediction engine — FieldIQ v3."""

from __future__ import annotations

import os
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.core.model_init import get_model, get_scaler
from app.core.config import (
    settings,
    DEFAULT_WEIGHTS,
    ELO_INDICES,
    FORM_INDICES,
    PDV_INDICES,
    XG_INDICES,
    SRR_INDICES,
    V3_FATIGUE_INDICES,
    V3_CHEMISTRY_INDICES,
    V3_MOMENTUM_INDICES,
    V3_TACTICAL_INDICES,
)
from app.data.seed_data import TEAMS, get_team_squad
from app.schemas.simulation import LayerToggles, SimulationWeights

from app.services.fatigue_engine import compute_travel_decay
from app.services.chemistry_engine import compute_synergy_differential, compute_xt_compatibility
from app.services.momentum_engine import (
    compute_clutch_differential,
    compute_penalty_composite,
    get_momentum_profile,
)
from app.services.psychological_engine import compute_squad_morale, morale_pass_completion_factor
from app.services.tactical_engine import (
    compute_tactical_differential,
    compute_press_efficacy,
    compute_defensive_line_risk,
)

CONF_ENC = {"UEFA": 0, "CONMEBOL": 1, "CONCACAF": 2, "CAF": 3, "AFC": 4, "OFC": 5}


@dataclass
class SimulationConfig:
    weights: SimulationWeights
    layers: LayerToggles


def apply_feature_weights(feat: np.ndarray, weights: SimulationWeights, layers: LayerToggles) -> np.ndarray:
    """Scale feature groups by user weights relative to defaults."""
    out = feat.copy()
    groups = [
        (ELO_INDICES, weights.elo_weight / DEFAULT_WEIGHTS["elo"]),
        (FORM_INDICES, weights.form_weight / DEFAULT_WEIGHTS["form"]),
        (PDV_INDICES, weights.pdv_weight / DEFAULT_WEIGHTS["pdv"]),
        (XG_INDICES, weights.xg_weight / DEFAULT_WEIGHTS["xg"]),
        (SRR_INDICES, weights.srr_weight / DEFAULT_WEIGHTS["srr"]),
    ]
    for indices, factor in groups:
        for i in indices:
            if i < len(out):
                out[i] *= factor

    if not layers.fatigue:
        for i in V3_FATIGUE_INDICES:
            if i < len(out):
                out[i] = 0.0
    if not layers.chemistry:
        for i in V3_CHEMISTRY_INDICES:
            if i < len(out):
                out[i] = 0.0
    if not layers.momentum:
        for i in V3_MOMENTUM_INDICES:
            if i < len(out):
                out[i] = 0.0
    if not layers.tactical:
        for i in V3_TACTICAL_INDICES:
            if i < len(out):
                out[i] = 0.0

    return out


def build_feature_vector(
    team_a: Dict,
    team_b: Dict,
    match_number: int = 1,
    ko_round: Optional[str] = None,
    rest_hours_a: float = 120.0,
    rest_hours_b: float = 120.0,
    players_a: Optional[List[Dict]] = None,
    players_b: Optional[List[Dict]] = None,
    config: Optional[SimulationConfig] = None,
) -> np.ndarray:
    """Construct the full 35-dimensional differential feature vector."""
    layers = config.layers if config else LayerToggles()
    use_psych = layers.psychological

    morale_a = compute_squad_morale(players_a) if use_psych and players_a else None
    morale_b = compute_squad_morale(players_b) if use_psych and players_b else None
    focus_a = morale_a["squad_focus_penalty"] if morale_a else 0.0
    focus_b = morale_b["squad_focus_penalty"] if morale_b else 0.0

    def pdv(t):
        return t.get("pdv", 0)

    def srr(t):
        return t.get("srr", 60) / 100.0

    base = np.array([
        (team_a["elo"] - team_b["elo"]) / 200.0,
        (team_b["rank"] - team_a["rank"]) / 50.0,
        float(team_a.get("wc_titles", 0) - team_b.get("wc_titles", 0)),
        (team_a.get("form", 60) - team_b.get("form", 60)) / 30.0,
        team_a.get("xg", 1.5) - team_b.get("xg", 1.5),
        team_b.get("xga", 1.2) - team_a.get("xga", 1.2),
        team_b.get("ppda", 11) - team_a.get("ppda", 11),
        team_a.get("deep_comp", 45) - team_b.get("deep_comp", 45),
        team_a.get("shot_acc", 0.32) - team_b.get("shot_acc", 0.32),
        team_a.get("set_piece", 0.10) - team_b.get("set_piece", 0.10),
        team_a.get("aerial", 0.60) - team_b.get("aerial", 0.60),
        pdv(team_b) - pdv(team_a),
        float(team_a.get("h2h", 0) - team_b.get("h2h", 0)),
        float(CONF_ENC.get(team_a.get("confederation", "UEFA"), 0)
              - CONF_ENC.get(team_b.get("confederation", "UEFA"), 0)),
        float(team_b.get("rank", 25) - team_a.get("rank", 25)) / 10.0,
        float(team_a.get("wc_apps", 5) - team_b.get("wc_apps", 5)),
        (team_a.get("qual_pts", 20) - team_b.get("qual_pts", 20)) / 10.0,
        (team_b.get("squad_age", 27) - team_a.get("squad_age", 27)) / 2.0,
        (team_a.get("caps_avg", 35) - team_b.get("caps_avg", 35)) / 20.0,
        0.0,
        0.0,
        srr(team_a) - srr(team_b),
        team_a.get("injury_penalty", 0.0) - team_b.get("injury_penalty", 0.0),
    ], dtype=np.float32)

    fatigue_diff = rest_decay_diff = tz_diff = 0.0
    if layers.fatigue:
        fa = compute_travel_decay(
            team_a.get("id", ""), match_number, ko_round, rest_hours_a,
            players=players_a,
            apply_psychological_circadian=use_psych,
        )
        fb = compute_travel_decay(
            team_b.get("id", ""), match_number, ko_round, rest_hours_b,
            players=players_b,
            apply_psychological_circadian=use_psych,
        )
        fatigue_diff = fb["cumulative_fatigue"] - fa["cumulative_fatigue"]
        rest_decay_diff = fb["rest_decay"] - fa["rest_decay"]
        tz_diff = float(fb["tz_shift_hours"] - fa["tz_shift_hours"]) / 12.0
    base[20] = float(fatigue_diff)

    synergy_diff = xt_diff = 0.0
    if layers.chemistry and players_a is not None and players_b is not None:
        synergy_diff = compute_synergy_differential(players_a, players_b)
        xt_a = compute_xt_compatibility(players_a)
        xt_b = compute_xt_compatibility(players_b)
        if use_psych:
            xt_a["xt_offensive_compat"] *= morale_pass_completion_factor(focus_a)
            xt_b["xt_offensive_compat"] *= morale_pass_completion_factor(focus_b)
        xt_diff = xt_a["xt_offensive_compat"] - xt_b["xt_offensive_compat"]

    clutch_diff = grd_diff = penalty_diff = 0.0
    if layers.momentum:
        clutch_diff = compute_clutch_differential(
            team_a.get("id", ""), team_b.get("id", ""), players_a, players_b,
            focus_penalty_a=focus_a, focus_penalty_b=focus_b,
        )
        pa = get_momentum_profile(team_a.get("id", ""))
        pb = get_momentum_profile(team_b.get("id", ""))
        grd_diff = pa["goal_response_delta"] - pb["goal_response_delta"]
        if players_a and players_b:
            penalty_diff = (
                compute_penalty_composite(players_a, focus_a)
                - compute_penalty_composite(players_b, focus_b)
            )
        else:
            penalty_diff = pa["penalty_composite"] - pb["penalty_composite"]
            if use_psych:
                penalty_diff -= (focus_a - focus_b) * 0.3

    tactical_diff = press_eff_diff = high_line_flag = late_drop_diff = 0.0
    if layers.tactical:
        tactical_diff = compute_tactical_differential(team_a, team_b)
        press_analysis = compute_press_efficacy(team_a, team_b)
        line_analysis = compute_defensive_line_risk(team_a, team_b)
        press_eff_diff = press_analysis["press_efficacy_delta"]
        high_line_flag = float(line_analysis["high_line_risk_flag"])
        late_drop_diff = press_analysis["late_game_drop"] - compute_press_efficacy(
            team_b, team_a
        )["late_game_drop"]

    v3_extension = np.array([
        fatigue_diff, rest_decay_diff, tz_diff,
        synergy_diff, xt_diff,
        clutch_diff, grd_diff, penalty_diff,
        tactical_diff, press_eff_diff, high_line_flag, late_drop_diff,
    ], dtype=np.float32)

    feat = np.concatenate([base, v3_extension])

    if config:
        feat = apply_feature_weights(feat, config.weights, config.layers)

    return feat


def predict_match(
    team_a: Dict,
    team_b: Dict,
    match_number: int = 1,
    ko_round: Optional[str] = None,
    rest_hours_a: float = 120.0,
    rest_hours_b: float = 120.0,
    players_a: Optional[List[Dict]] = None,
    players_b: Optional[List[Dict]] = None,
    config: Optional[SimulationConfig] = None,
) -> np.ndarray:
    """Returns [p_win, p_draw, p_loss] for team_a vs team_b."""
    if players_a is None:
        players_a = get_team_squad(team_a.get("id", ""))
    if players_b is None:
        players_b = get_team_squad(team_b.get("id", ""))

    model = get_model()
    scaler = get_scaler()

    feat = build_feature_vector(
        team_a, team_b, match_number, ko_round,
        rest_hours_a, rest_hours_b, players_a, players_b, config,
    ).reshape(1, -1)

    if feat.shape[1] != scaler.n_features_in_:
        feat_compat = np.zeros((1, scaler.n_features_in_), dtype=np.float32)
        common = min(feat.shape[1], scaler.n_features_in_)
        feat_compat[0, :common] = feat[0, :common]
        feat = feat_compat

    feat_scaled = scaler.transform(feat)
    if os.getenv("SKIP_MODEL_INIT") == "1":
        out = model.predict_proba(feat_scaled)
        return np.asarray(out)[0]

    import torch
    x = torch.FloatTensor(feat_scaled)
    return model.predict_proba(x).numpy()[0]


def simulate_match_goals(
    team_a: Dict,
    team_b: Dict,
    probs: np.ndarray,
    rng: np.random.Generator,
) -> Tuple[int, int, int]:
    """
    Simulate goals consistent with model probabilities.
    Returns (goals_a, goals_b, outcome) where outcome is 0=win, 1=draw, 2=loss for team_a.
    """
    p_win, p_draw, p_loss = probs
    strength_a = p_win + 0.5 * p_draw
    strength_b = p_loss + 0.5 * p_draw

    xg_a = max(0.3, team_a.get("xg", 1.5) * (0.65 + 0.70 * strength_a))
    xg_b = max(0.3, team_b.get("xg", 1.5) * (0.65 + 0.70 * strength_b))

    goals_a = int(rng.poisson(xg_a))
    goals_b = int(rng.poisson(xg_b))

    if goals_a > goals_b:
        outcome = 0
    elif goals_a < goals_b:
        outcome = 2
    else:
        outcome = 1

    return goals_a, goals_b, outcome


def pdv_cascade_penalty(team: Dict, ko_round: int) -> float:
    pdv = team.get("pdv", 0)
    base_susp_prob = min(0.85, pdv * 0.12 * ko_round)
    return max(0.60, 1.0 - base_susp_prob * 0.14)


def apply_roster_injuries(
    teams: List[Dict],
    injuries: Dict[str, List[str]],
    player_ratings: Dict[str, int],
) -> List[Dict]:
    teams_copy = [dict(t) for t in teams]
    for team in teams_copy:
        team_injuries = injuries.get(team["id"], [])
        if not team_injuries:
            continue
        xg_pen = srr_pen = 0.0
        for pid in team_injuries:
            rating = player_ratings.get(pid, 80)
            xg_pen += (rating - 70) * 0.018
            srr_pen += (rating - 70) * 0.25
        team["xg"] = max(0.3, team["xg"] - xg_pen)
        team["srr"] = max(20, team.get("srr", 60) - srr_pen)
        team["injury_penalty"] = xg_pen
    return teams_copy


def simulate_ko_match(
    team_a: Dict,
    team_b: Dict,
    ko_round_num: int,
    ko_round_name: str,
    rng: np.random.Generator,
    config: Optional[SimulationConfig] = None,
    rest_hours_a: float = 120.0,
    rest_hours_b: float = 120.0,
    match_number: int = 4,
) -> Dict:
    """Knockout match — no draws. PDV cascade + v3 layers applied."""
    players_a = get_team_squad(team_a.get("id", ""))
    players_b = get_team_squad(team_b.get("id", ""))

    probs = predict_match(
        team_a, team_b,
        match_number=match_number,
        ko_round=ko_round_name,
        rest_hours_a=rest_hours_a,
        rest_hours_b=rest_hours_b,
        players_a=players_a,
        players_b=players_b,
        config=config,
    )
    p_win, p_draw, p_loss = probs
    total = p_win + p_loss
    if total < 1e-9:
        return team_a if rng.random() < 0.5 else team_b

    p_win_adj = (p_win + p_draw * (p_win / total)) * pdv_cascade_penalty(team_a, ko_round_num)
    p_win_adj = max(0.05, min(0.95, p_win_adj))
    return team_a if rng.random() < p_win_adj / (p_win_adj + (1.0 - p_win_adj)) else team_b


def run_group_stage(
    groups: List[List[Dict]],
    rng: np.random.Generator,
    config: Optional[SimulationConfig] = None,
):
    qualified = []
    group_results = []

    for gi, group in enumerate(groups):
        pts = {t["id"]: 0 for t in group}
        gf = {t["id"]: 0 for t in group}
        ga = {t["id"]: 0 for t in group}

        for ai, bi in [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]:
            ta, tb = group[ai], group[bi]
            probs = predict_match(
                ta, tb,
                match_number=gi % 3 + 1,
                players_a=get_team_squad(ta["id"]),
                players_b=get_team_squad(tb["id"]),
                config=config,
            )
            goals_a, goals_b, outcome = simulate_match_goals(ta, tb, probs, rng)

            gf[ta["id"]] += goals_a
            ga[ta["id"]] += goals_b
            gf[tb["id"]] += goals_b
            ga[tb["id"]] += goals_a

            if outcome == 0:
                pts[ta["id"]] += 3
            elif outcome == 1:
                pts[ta["id"]] += 1
                pts[tb["id"]] += 1
            else:
                pts[tb["id"]] += 3

        ranked = sorted(
            group,
            key=lambda t: (pts[t["id"]], gf[t["id"]] - ga[t["id"]], gf[t["id"]]),
            reverse=True,
        )
        qualified.extend(ranked[:2])
        group_results.append({
            "group": chr(65 + gi),
            "teams": [
                {
                    "name": t["name"],
                    "flag": t["flag"],
                    "pts": pts[t["id"]],
                    "gf": gf[t["id"]],
                    "ga": ga[t["id"]],
                    "gd": gf[t["id"]] - ga[t["id"]],
                    "advance": i < 2,
                }
                for i, t in enumerate(ranked)
            ],
        })

    return qualified, group_results


def run_tournament_once(
    teams: List[Dict],
    rng: np.random.Generator,
    config: Optional[SimulationConfig] = None,
):
    groups = [teams[i:i + 4] for i in range(0, 48, 4)]
    qualified, group_results = run_group_stage(groups, rng, config)

    bracket = qualified[:32]
    ko_results = {}
    round_names = ["Round of 32", "Round of 16", "Quarter-finals", "Semi-finals"]

    for ri, rname in enumerate(round_names, 1):
        rest_base = 96 + rng.uniform(-12, 24)
        next_round = []
        for i in range(0, len(bracket), 2):
            if i + 1 >= len(bracket):
                next_round.append(bracket[i])
                continue
            winner = simulate_ko_match(
                bracket[i], bracket[i + 1], ri, rname, rng,
                config=config,
                rest_hours_a=rest_base,
                rest_hours_b=rest_base + rng.uniform(-24, 24),
                match_number=ri + 3,
            )
            next_round.append(winner)
        ko_results[rname] = [{"name": t["name"], "flag": t["flag"]} for t in next_round]
        bracket = next_round

    if len(bracket) < 2:
        champion = bracket[0] if bracket else teams[0]
        return champion, champion, teams[1], group_results, ko_results

    while len(bracket) > 1:
        if len(bracket) == 2:
            finalist_a, finalist_b = bracket[0], bracket[1]
            champion = simulate_ko_match(
                finalist_a, finalist_b, 6, "Final", rng,
                config=config, match_number=8,
            )
            return champion, finalist_a, finalist_b, group_results, ko_results
        next_round = []
        for i in range(0, len(bracket), 2):
            if i + 1 >= len(bracket):
                next_round.append(bracket[i])
            else:
                next_round.append(
                    simulate_ko_match(
                        bracket[i], bracket[i + 1], 5, "Semi-finals", rng,
                        config=config, match_number=7,
                    )
                )
        bracket = next_round

    champion = bracket[0]
    return champion, champion, champion, group_results, ko_results


def run_monte_carlo(
    teams: List[Dict],
    n_sims: int = 10_000,
    injuries: Optional[Dict] = None,
    player_ratings: Optional[Dict] = None,
    config: Optional[SimulationConfig] = None,
) -> Dict:
    """Run n_sims full tournament simulations with all v3 layers active."""
    teams = [dict(t) for t in teams]
    if injuries:
        teams = apply_roster_injuries(teams, injuries, player_ratings or {})

    champ_counts: Dict[str, int] = {}

    for sim_i in range(n_sims):
        rng = np.random.default_rng(seed=sim_i + 1000)
        champion, *_ = run_tournament_once(teams, rng, config)
        name = champion["name"]
        champ_counts[name] = champ_counts.get(name, 0) + 1

    display_rng = np.random.default_rng(seed=42)
    champion, finalist_a, finalist_b, group_results, ko_results = run_tournament_once(
        teams, display_rng, config
    )

    champion_probs = {
        k: round(v / n_sims, 4)
        for k, v in sorted(champ_counts.items(), key=lambda x: -x[1])
    }

    layers = config.layers if config else LayerToggles()
    weights = config.weights if config else SimulationWeights()

    return {
        "version": "3.0",
        "n_simulations": n_sims,
        "champion_probs": champion_probs,
        "display_champion": {
            "name": champion["name"],
            "flag": champion["flag"],
            "elo": champion["elo"],
            "pdv": champion["pdv"],
        },
        "display_finalist_a": {"name": finalist_a["name"], "flag": finalist_a["flag"]},
        "display_finalist_b": {"name": finalist_b["name"], "flag": finalist_b["flag"]},
        "group_results": group_results,
        "ko_results": ko_results,
        "v3_layers_active": [
            name for name, on in [
                ("fatigue_travel", layers.fatigue),
                ("chemistry_synergy", layers.chemistry),
                ("momentum_clutch", layers.momentum),
                ("tactical_matchup", layers.tactical),
                ("psychological_context", layers.psychological),
            ] if on
        ],
        "weights_used": {
            "elo": weights.elo_weight,
            "form": weights.form_weight,
            "pdv": weights.pdv_weight,
            "xg": weights.xg_weight,
            "srr": weights.srr_weight,
        },
        "v3_layers": {
            "fatigue": layers.fatigue,
            "chemistry": layers.chemistry,
            "momentum": layers.momentum,
            "tactical": layers.tactical,
            "psychological": layers.psychological,
        },
    }
