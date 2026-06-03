"""Pytest fixtures for FieldIQ API tests."""

import os
import pytest

os.environ.setdefault("SKIP_MODEL_INIT", "1")
os.environ.setdefault("MODEL_PATH", os.path.join(os.environ.get("TEMP", "/tmp"), "fieldiq_test", "match_mlp.pt"))
os.environ.setdefault("SCALER_PATH", os.path.join(os.environ.get("TEMP", "/tmp"), "fieldiq_test", "scaler.joblib"))
os.environ.setdefault("ENFORCE_CREDITS", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def model_ready(client):
    r = client.get("/health")
    assert r.status_code == 200
    return r.json()
