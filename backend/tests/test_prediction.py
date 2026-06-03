"""Feature vector and prediction engine tests."""

import numpy as np
import pytest

from app.core.config import N_FEATURES
from app.data.seed_data import TEAMS, get_team_squad
from app.schemas.simulation import SimulationWeights, LayerToggles
from app.services.prediction import (
    SimulationConfig,
    build_feature_vector,
    predict_match,
    simulate_match_goals,
    apply_feature_weights,
)


def test_feature_vector_dimension():
    a, b = TEAMS[0], TEAMS[1]
    feat = build_feature_vector(a, b, players_a=get_team_squad(a["id"]), players_b=get_team_squad(b["id"]))
    assert feat.shape == (N_FEATURES,)


def test_feature_weights_change_output():
    a, b = TEAMS[0], TEAMS[1]
    base = build_feature_vector(a, b)
    heavy_elo = apply_feature_weights(
        base,
        SimulationWeights(elo_weight=0.80, form_weight=0.25, pdv_weight=0.20, xg_weight=0.15, srr_weight=0.10),
        LayerToggles(),
    )
    assert not np.allclose(base, heavy_elo)


def test_layer_toggle_zeros_v3():
    a, b = TEAMS[0], TEAMS[1]
    feat = build_feature_vector(
        a, b,
        players_a=get_team_squad(a["id"]),
        players_b=get_team_squad(b["id"]),
        config=SimulationConfig(
            weights=SimulationWeights(),
            layers=LayerToggles(chemistry=False, momentum=False, tactical=False, fatigue=False),
        ),
    )
    assert feat[23:].sum() == 0.0


def test_predict_match_probabilities_sum():
    try:
        import torch  # noqa: F401
    except OSError:
        pytest.skip("PyTorch unavailable in this environment")
    probs = predict_match(TEAMS[0], TEAMS[1])
    assert len(probs) == 3
    assert abs(probs.sum() - 1.0) < 0.01
    assert all(p >= 0 for p in probs)


def test_simulate_goals_consistent_with_outcome():
    rng = np.random.default_rng(42)
    for _ in range(50):
        ga, gb, outcome = simulate_match_goals(TEAMS[0], TEAMS[1], np.array([0.5, 0.25, 0.25]), rng)
        if ga > gb:
            assert outcome == 0
        elif ga < gb:
            assert outcome == 2
        else:
            assert outcome == 1


def test_get_team_squad_returns_eleven():
    squad = get_team_squad("FRA")
    assert len(squad) == 11
    assert all("pos" in p for p in squad)
