"""Health and root endpoint tests."""

def test_health(client, model_ready):
    data = model_ready
    assert data["status"] == "ok"
    assert data["version"] == "3.0.0"
    assert data["features"] == 35
    assert len(data["layers"]) == 7
    assert "psychological_context" in data["layers"]
    assert "command_center" in data["layers"]
    assert "deep_intelligence" in data["layers"]


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "docs" in r.json()
