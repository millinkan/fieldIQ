"""Layer 5 psychological context engine tests."""

from app.data.seed_data import get_team_squad
from app.services.fatigue_engine import compute_travel_decay
from app.services.psychological_engine import (
    apply_circadian_to_fatigue,
    compute_player_morale,
    compute_squad_circadian,
    compute_squad_morale,
)
from app.services.momentum_engine import compute_penalty_composite


def test_vinicius_morale_active_on_spike():
    m = compute_player_morale("vinicius")
    assert m["active"] is True
    assert m["focus_decay"] >= 0.03
    assert m["toxicity_ratio"] >= 3.0


def test_casemiro_morale_inactive_without_spike():
    m = compute_player_morale("casemiro")
    assert m["active"] is False
    assert m["focus_decay"] == 0.0


def test_circadian_overlay_adds_not_replaces():
    base = {"cumulative_fatigue": 0.20, "sprint_speed_mult": 0.95, "defensive_recovery": 0.96}
    circadian = {"circadian_fatigue_uplift": 0.02, "circadian_multiplier": 0.04, "squad_circadian_score": 0.12}
    out = apply_circadian_to_fatigue(base, circadian)
    assert out["base_cumulative_fatigue"] == 0.20
    assert out["cumulative_fatigue"] == 0.22
    assert out["circadian_fatigue_uplift"] == 0.02


def test_squad_circadian_caps_players():
    squad = get_team_squad("BRA")
    c = compute_squad_circadian(squad, rest_hours=72, base_fatigue=0.18)
    assert len(c.get("flagged_players", [])) <= 3
    assert c["circadian_fatigue_uplift"] <= 0.08


def test_fatigue_engine_circadian_integration():
    squad = get_team_squad("BRA")
    plain = compute_travel_decay("BRA", 3, rest_hours=72, apply_psychological_circadian=False)
    with_psych = compute_travel_decay(
        "BRA", 3, rest_hours=72, players=squad, apply_psychological_circadian=True
    )
    assert with_psych["cumulative_fatigue"] >= plain["cumulative_fatigue"]
    assert "base_cumulative_fatigue" in with_psych


def test_morale_reduces_penalty_composite():
    squad = get_team_squad("BRA")
    morale = compute_squad_morale(squad)
    base = compute_penalty_composite(squad, 0.0)
    adjusted = compute_penalty_composite(squad, morale["squad_focus_penalty"])
    if morale["squad_focus_penalty"] > 0:
        assert adjusted < base
