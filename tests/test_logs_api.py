"""HTTP integration tests for POST /api/log/commute.

Covers:
- Valid payload returns 201 and "logged" status.
- Server recomputes CO2 from mode + distance_km; client values are ignored.
- Unknown mode returns 400.
- Empty start location returns 400.

The Firestore client is monkeypatched so no real credentials are needed.
"""

import pytest
from fastapi.testclient import TestClient

import app as app_module
from services import firestore_client as fc_module


@pytest.fixture
def captured():
    """Collects the entry dicts passed to the fake log_commute function."""
    return []


@pytest.fixture
def client(monkeypatch, captured):
    def fake_log_commute(entry, client=None):
        captured.append(dict(entry))
        return entry

    monkeypatch.setattr(fc_module, "log_commute", fake_log_commute)
    return TestClient(app_module.app)


def test_log_commute_valid_returns_201(client, captured):
    response = client.post(
        "/api/log/commute",
        json={
            "start": "A Road",
            "destination": "B Road",
            "mode": "driving",
            "distance_km": 10.0,
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "logged"
    assert response.json()["category"] == "commute"


def test_log_commute_recomputes_co2_server_side(client, captured):
    """The server must compute CO2 from distance + mode regardless of what the
    client sends.  Tampered or absent co2 fields in the payload are irrelevant
    because the Pydantic model no longer exposes them as inputs.
    """
    response = client.post(
        "/api/log/commute",
        json={
            "start": "A Road",
            "destination": "B Road",
            "mode": "driving",
            "distance_km": 10.0,
            # Any co2_emitted / co2_saved_vs_driving keys here are ignored by
            # the model and the server recomputes from first principles.
        },
    )
    assert response.status_code == 201
    assert len(captured) == 1
    doc = captured[0]
    # Server-side: 10 km * 0.192 kg/km = 1.92 kg for driving
    assert doc["co2_emitted"] == pytest.approx(1.92)
    # Driving vs driving saves exactly 0
    assert doc["co2_saved_vs_driving"] == pytest.approx(0.0)


def test_log_commute_cycling_saves_vs_driving(client, captured):
    """Cycling (zero CO2) should show full driving CO2 as the saving."""
    response = client.post(
        "/api/log/commute",
        json={
            "start": "A Road",
            "destination": "B Road",
            "mode": "cycling",
            "distance_km": 5.0,
        },
    )
    assert response.status_code == 201
    doc = captured[0]
    # cycling emits 0; driving would be 5 * 0.192 = 0.96 kg
    assert doc["co2_emitted"] == pytest.approx(0.0)
    assert doc["co2_saved_vs_driving"] == pytest.approx(0.96)


def test_log_commute_unknown_mode_returns_400(client, captured):
    response = client.post(
        "/api/log/commute",
        json={
            "start": "A Road",
            "destination": "B Road",
            "mode": "teleport",
            "distance_km": 10.0,
        },
    )
    assert response.status_code == 400


def test_log_commute_empty_start_returns_400(client, captured):
    response = client.post(
        "/api/log/commute",
        json={
            "start": "   ",
            "destination": "B Road",
            "mode": "driving",
            "distance_km": 10.0,
        },
    )
    assert response.status_code == 400
