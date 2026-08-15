"""
End-to-end FastAPI tests using TestClient.

The app uses a single module-level in-memory store (backend.app.storage
.memory_store.store), so these tests clear it before each test to stay
isolated from one another.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.storage.memory_store import store

@pytest.fixture(autouse=True)
def clear_store():
    store.clear()
    yield
    store.clear()

client = TestClient(app)

VALID_READING = {
    "timestamp": "2026-01-01T00:00:00Z",
    "drone_id": "drone-1",
    "source": "mock",
    "position": {"x": 1.0, "y": 2.0, "z": 1.0},
    "gas": {"ch4_ppm": 400.0, "co_ppm": 2.0, "co2_ppm": 450.0, "o2_percent": 20.9},
}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "mine-drone-risk-backend"}

def test_post_reading_then_read_it_back():
    post_response = client.post("/api/readings", json=VALID_READING)

    assert post_response.status_code == 200
    body = post_response.json()
    assert body["message"] == "reading_saved"
    assert body["total_readings"] == 1
    get_response = client.get("/api/readings")
    assert get_response.status_code == 200
    assert get_response.json()["count"] == 1

def test_post_reading_then_get_current_risk():
    client.post("/api/readings", json=VALID_READING)

    response = client.get("/api/risk/current")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "risk_calculated"
    assert body["risk"]["risk_level"] == "low"
    assert body["risk"]["risk_score"] == 0.0

def test_get_current_risk_with_no_readings():
    response = client.get("/api/risk/current")
    assert response.status_code == 200
    assert response.json() == {"message": "no_readings_available", "risk": None}

def test_post_reading_rejects_invalid_payload():
    invalid_reading = dict(VALID_READING)
    invalid_reading["gas"] = dict(VALID_READING["gas"])
    invalid_reading["gas"]["ch4_ppm"] = -10.0  

    response = client.post("/api/readings", json=invalid_reading)
    assert response.status_code == 422

def test_drone_status_round_trip():
    status_payload = {
        "drone_id": "drone-1",
        "status": "active",
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
    }

    post_response = client.post("/api/drone/status", json=status_payload)
    assert post_response.status_code == 200
    get_response = client.get("/api/drone/status/drone-1")
    assert get_response.status_code == 200
    assert get_response.json()["status"]["status"] == "active"

def test_get_unknown_drone_status_is_404():
    response = client.get("/api/drone/status/does-not-exist")
    assert response.status_code == 404
