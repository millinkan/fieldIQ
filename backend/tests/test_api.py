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


def test_pdv_scores(client):
    r = client.get("/v1/pdv/scores")
    assert r.status_code == 200
    assert len(r.json()["players"]) > 0
