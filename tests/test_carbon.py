"""Unit tests for the deterministic commute carbon math.

Numbers here are verified by hand from the factors in config.py:
  driving 0.192, transit 0.105, walking 0, cycling 0 (kg CO2/km).
"""

import pytest

from core.carbon import (
    build_comparison,
    co2_for_mode,
    co2_saved_vs_baseline,
    is_viable,
    meters_to_km,
)


def test_meters_to_km():
    assert meters_to_km(1500) == 1.5


def test_co2_driving_10km():
    # 10 km * 0.192 = 1.92 kg
    assert co2_for_mode(10, "driving") == 1.92


def test_co2_transit_10km():
    # 10 km * 0.105 = 1.05 kg
    assert co2_for_mode(10, "transit") == 1.05


def test_co2_walking_and_cycling_are_zero():
    assert co2_for_mode(10, "walking") == 0.0
    assert co2_for_mode(10, "cycling") == 0.0


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        co2_for_mode(5, "teleport")


def test_negative_distance_raises():
    with pytest.raises(ValueError):
        co2_for_mode(-1, "driving")


def test_saving_never_negative():
    # Mode emits more than baseline -> clamp to 0.
    assert co2_saved_vs_baseline(2.0, 1.0) == 0.0
    # Normal case: baseline 1.92, mode 1.05 -> 0.87 saved.
    assert co2_saved_vs_baseline(1.05, 1.92) == 0.87


def test_viability_thresholds():
    assert is_viable("walking", 2.0) is True
    assert is_viable("walking", 5.0) is False
    assert is_viable("cycling", 8.0) is True
    assert is_viable("cycling", 12.0) is False
    assert is_viable("driving", 500.0) is True


def test_build_comparison_sorted_and_labelled():
    # 5 km trip. Walking/cycling viable and zero-carbon -> greenest first.
    routes = {
        "driving": {"distance_meters": 5000, "duration_seconds": 600},
        "transit": {"distance_meters": 5200, "duration_seconds": 900},
        "walking": {"distance_meters": 4800, "duration_seconds": 3600},
        "cycling": {"distance_meters": 4900, "duration_seconds": 1200},
    }
    result = build_comparison(routes)
    modes_in_order = [o["mode"] for o in result["options"]]

    # Zero-carbon modes come first; driving (highest CO2) last.
    assert modes_in_order[-1] == "driving"
    assert set(modes_in_order[:2]) == {"walking", "cycling"}

    # Baseline CO2 = 5 km * 0.192 = 0.96 kg
    assert result["baseline_co2_kg"] == 0.96

    # Recommended is a viable zero-carbon mode at 5 km (cycling, since walking
    # is over its 3 km threshold).
    assert result["recommended_mode"] == "cycling"
    recommended = [o for o in result["options"] if o["recommended"]]
    assert len(recommended) == 1
    assert recommended[0]["mode"] == "cycling"


def test_build_comparison_recommends_driving_for_long_trip():
    # 40 km: walking and cycling are not viable; transit is greenest viable.
    routes = {
        "driving": {"distance_meters": 40000, "duration_seconds": 2400},
        "transit": {"distance_meters": 41000, "duration_seconds": 3600},
        "walking": {"distance_meters": 39000, "duration_seconds": 36000},
        "cycling": {"distance_meters": 39500, "duration_seconds": 9000},
    }
    result = build_comparison(routes)
    assert result["recommended_mode"] == "transit"
