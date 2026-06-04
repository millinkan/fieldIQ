"""Command Center and Deep Intelligence API tests."""

import pytest


@pytest.fixture
def match_body():
    return {
        "home_id": "BRA",
        "away_id": "FRA",
        "ko_round": "Quarter-finals",
        "match_number": 5,
        "rest_hours_a": 120.0,
        "rest_hours_b": 120.0,
        "market_odds": {"home_win": 0.42, "draw": 0.24, "away_win": 0.34},
    }


def test_command_fixtures(client):
    r = client.get("/v1/command/fixtures")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert "home_id" in data["fixtures"][0]


def test_command_delta(client, match_body):
    r = client.post("/v1/command/delta", json=match_body)
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "3.0"
    assert "probabilities" in data
    assert "edge" in data
    assert "prob_discrepancy_home" in data["probabilities"]
    assert "primary_driver" in data["edge"]


def test_command_delta_unknown_team(client, match_body):
    body = {**match_body, "home_id": "XXX"}
    r = client.post("/v1/command/delta", json=body)
    assert r.status_code == 404


def test_deep_pathways(client, match_body):
    r = client.post("/v1/deep/pathways", json={**match_body, "n_sims": 500})
    assert r.status_code == 200
    data = r.json()
    assert "clusters" in data
    assert len(data["clusters"]) >= 1
    assert "dominant_pathway" in data


def test_deep_sensitivity(client, match_body):
    r = client.post("/v1/deep/sensitivity", json=match_body)
    assert r.status_code == 200
    data = r.json()
    assert "shocks" in data
    assert len(data["shocks"]) >= 1


def test_deep_asymmetry(client, match_body):
    r = client.post("/v1/deep/asymmetry", json=match_body)
    assert r.status_code == 200
    data = r.json()
    assert "severity_label" in data
    assert "overall_asymmetry_rating" in data


def test_deep_full(client, match_body):
    r = client.post("/v1/deep/full", json={**match_body, "n_sims": 500})
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "4.0"
    assert "pathways" in data
    assert "sensitivity" in data
    assert "asymmetry" in data
    assert "executive_summary" in data
    assert data["executive_summary"].get("one_line")
