import pytest
from fastapi.testclient import TestClient
from server.main import create_app
from simulation.config import SimConfig

@pytest.fixture
def client():
    app = create_app(SimConfig(seed=42, num_agents=5, grid_size=5, tick_rate_hz=0))
    return TestClient(app)

def test_get_state_returns_200(client):
    resp = client.get("/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("running", "paused")

def test_post_control_pause(client):
    resp = client.post("/control", json={"command": "pause"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"

def test_post_control_resume(client):
    client.post("/control", json={"command": "pause"})
    resp = client.post("/control", json={"command": "resume"})
    assert resp.json()["status"] == "running"

def test_get_snapshots_empty(client):
    resp = client.get("/snapshots")
    assert resp.status_code == 200
    assert resp.json() == []

def test_get_metrics_returns_list(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
