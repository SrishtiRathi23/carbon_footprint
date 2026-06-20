"""Integration test for the comparison endpoint.

The Maps API and Gemini are both mocked so the test is hermetic. It checks
that /api/compare returns results sorted greenest-first with exactly one
recommended, viable option.
"""

import pytest
from fastapi.testclient import TestClient

import app as app_module
from routes import compare as compare_module


@pytest.fixture
def client(monkeypatch):
    def fake_routes(start, destination):
        return {
            "driving": {"distance_meters": 5000, "duration_seconds": 600},
            "transit": {"distance_meters": 5200, "duration_seconds": 900},
            "walking": {"distance_meters": 4800, "duration_seconds": 3600},
            "cycling": {"distance_meters": 4900, "duration_seconds": 1200},
        }

    monkeypatch.setattr(compare_module, "fetch_all_routes", fake_routes)
    monkeypatch.setattr(compare_module, "generate_tip", lambda comparison: "test tip")
    return TestClient(app_module.app)


def test_compare_returns_sorted_labelled_results(client):
    response = client.post(
        "/api/compare", json={"start": "A Road", "destination": "B Road"}
    )
    assert response.status_code == 200
    data = response.json()

    options = data["options"]
    assert len(options) == 4

    # Sorted greenest-first: CO2 must be non-decreasing.
    co2_values = [o["co2_emitted_kg"] for o in options]
    assert co2_values == sorted(co2_values)

    # Exactly one recommended option, and it must be viable.
    recommended = [o for o in options if o["recommended"]]
    assert len(recommended) == 1
    assert recommended[0]["viable"] is True

    # Driving baseline = 5 km * 0.192 = 0.96
    assert data["baseline_co2_kg"] == 0.96
    assert data["tip"] == "test tip"


def test_compare_rejects_empty_input(client):
    response = client.post("/api/compare", json={"start": "   ", "destination": "B"})
    assert response.status_code == 400


def test_compare_404_when_no_routes(client, monkeypatch):
    monkeypatch.setattr(
        compare_module,
        "fetch_all_routes",
        lambda start, destination: {
            "driving": None,
            "transit": None,
            "walking": None,
            "cycling": None,
        },
    )
    response = client.post(
        "/api/compare", json={"start": "Nowhere", "destination": "Void"}
    )
    assert response.status_code == 404
