"""API integration tests."""


def test_teams_list(client):
    r = client.get("/v1/tournament/teams")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 48


def test_simulate_small(client):
    r = client.post("/v1/tournament/simulate", json={
        "n_simulations": 100,
        "elo_weight": 0.50,
        "use_cache": False,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "3.0"
    assert data["n_simulations"] == 100
    assert len(data["champion_probs"]) > 0
    assert data["weights_used"]["elo"] == 0.50
    assert "group_results" in data


def test_model_architecture_v3(client):
    r = client.get("/v1/model/architecture")
    assert r.status_code == 200
    data = r.json()
    assert data["input_features"] == 35
    assert data["version"] == "3.0"


def test_srr_rankings(client):
    r = client.get("/v1/srr/rankings?scenario=striker")
    assert r.status_code == 200
    data = r.json()
    assert len(data["rankings"]) > 0
    assert isinstance(data["rankings"][0]["srr"], (int, float))


def test_v3_fatigue(client):
    r = client.get("/v1/v3/fatigue/BRA?match_number=2")
    assert r.status_code == 200
    assert "cumulative_fatigue" in r.json()


def test_v3_psychological_team(client):
    r = client.get("/v1/v3/psychological/BRA?match_number=3&rest_hours=72")
    assert r.status_code == 200
    data = r.json()
    assert data["layer"] == "psychological_context"
    assert "morale" in data
    assert "circadian" in data


def test_v3_psychological_player_vinicius(client):
    r = client.get("/v1/v3/psychological/player/vinicius")
    assert r.status_code == 200
    assert r.json()["targeted_morale"]["active"] is True


def test_full_analysis_includes_layer5(client):
    r = client.post("/v1/v3/full-analysis", json={
        "team_a": {"id": "BRA", "name": "Brazil"},
        "team_b": {"id": "FRA", "name": "France"},
        "match_number": 3,
        "enable_psychological": True,
    })
    assert r.status_code == 200
    assert "layer_5_psychological" in r.json()["layers"]


def test_pdv_scores(client):
    r = client.get("/v1/pdv/scores")
    assert r.status_code == 200
    assert len(r.json()["players"]) > 0


def test_pdv_cascade_not_found(client):
    r = client.post("/v1/pdv/cascade", json={"player_id": "nonexistent"})
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_pdv_cascade_ok(client):
    r = client.post("/v1/pdv/cascade", json={"player_id": "casemiro", "match_number": 3})
    assert r.status_code == 200
    data = r.json()
    assert data["player_id"] == "casemiro"
    assert "suspension_prob" in data


def test_roster_players_synthetic(client):
    r = client.get("/v1/squad/players/FRA")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 11
    assert data["players"][0]["team_id"] == "FRA"


def test_roster_synergy_opponent(client):
    r = client.post("/v1/squad/synergy", json={
        "team_id": "BRA",
        "opponent_id": "FRA",
        "player_statuses": [{"player_id": p["id"], "status": "ok"} for p in [
            {"id": "alisson"}, {"id": "militao"}, {"id": "marquinhos"},
        ]],
    })
    assert r.status_code == 200
    data = r.json()
    assert "opponent_adjustments" in data
    assert data["opponent_id"] == "FRA"


def test_fixtures_mock(client):
    r = client.get("/v1/model/fixtures")
    assert r.status_code == 200
    data = r.json()
    assert "fixtures" in data
    assert data["provider"] == "mock"


def test_credits_balance(client):
    r = client.get("/v1/credits/balance?tier=pro", headers={"X-API-Key": "demo"})
    assert r.status_code == 200
    assert "credits_remaining" in r.json()
