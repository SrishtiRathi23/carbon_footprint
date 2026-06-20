"""Deterministic commute carbon math.

Pure functions only -- no network, no I/O, no global state. Given a distance
and a travel mode, the CO2 is fully determined by the fixed factors in
``config.py``. This is what makes the result auditable and unit-testable:
the same inputs always yield the same number, and the number never comes
from an LLM.

Carbon model assumption:
    co2_kg = distance_km * emission_factor[mode]

Distances come from the Google Maps Routes API (real road/route distance),
not straight-line, so the factor is applied to actual travelled distance.
"""

from typing import Dict, List, Optional

from .config import (
    BASELINE_MODE,
    COMMUTE_EMISSION_FACTORS,
    VIABILITY_MAX_KM,
)


def meters_to_km(distance_meters: float) -> float:
    """Convert a distance in metres to kilometres."""
    return distance_meters / 1000.0


def co2_for_mode(distance_km: float, mode: str) -> float:
    """Return kg CO2 for travelling ``distance_km`` by ``mode``.

    Raises ``ValueError`` for an unknown mode so a bad call fails loudly
    rather than silently returning a wrong (or zero) number.
    """
    if mode not in COMMUTE_EMISSION_FACTORS:
        raise ValueError(f"Unknown travel mode: {mode!r}")
    if distance_km < 0:
        raise ValueError("distance_km must be non-negative")
    return round(distance_km * COMMUTE_EMISSION_FACTORS[mode], 3)


def co2_saved_vs_baseline(mode_co2_kg: float, baseline_co2_kg: float) -> float:
    """CO2 saved (kg) by choosing a mode instead of the baseline (driving).

    Never returns a negative saving: if a mode emits more than driving, the
    saving is clamped to 0 so the headline "saved" total cannot go down.
    """
    return round(max(0.0, baseline_co2_kg - mode_co2_kg), 3)


def is_viable(mode: str, distance_km: float) -> bool:
    """Whether ``mode`` is a realistic choice for a trip of ``distance_km``.

    Zero-carbon modes (walking, cycling) are only "viable" within a sane
    distance so we do not recommend walking 40 km. Thresholds live in
    ``config.VIABILITY_MAX_KM`` and are documented as assumptions.
    """
    max_km = VIABILITY_MAX_KM.get(mode)
    if max_km is None:
        return True
    return distance_km <= max_km


def build_comparison(routes: Dict[str, Optional[dict]]) -> dict:
    """Assemble the full comparison result from raw per-mode route data.

    ``routes`` maps each mode to either ``None`` (no route found / API gave
    nothing for that mode) or a dict with at least ``distance_meters`` and
    ``duration_seconds``.

    Returns a dict with:
      - ``options``: list of per-mode results, sorted greenest-first
        (lowest CO2, then shortest duration), each tagged ``viable`` and
        the single best one tagged ``recommended``.
      - ``baseline_co2_kg``: driving CO2, used for the saved-vs-driving math.
    """
    baseline = routes.get(BASELINE_MODE)
    baseline_co2 = (
        co2_for_mode(meters_to_km(baseline["distance_meters"]), BASELINE_MODE)
        if baseline
        else 0.0
    )

    options: List[dict] = []
    for mode, data in routes.items():
        if not data:
            continue
        distance_km = round(meters_to_km(data["distance_meters"]), 3)
        mode_co2 = co2_for_mode(distance_km, mode)
        options.append(
            {
                "mode": mode,
                "distance_km": distance_km,
                "duration_seconds": data.get("duration_seconds"),
                "co2_emitted_kg": mode_co2,
                "co2_saved_vs_driving_kg": co2_saved_vs_baseline(
                    mode_co2, baseline_co2
                ),
                "viable": is_viable(mode, distance_km),
            }
        )

    # Greenest first: lowest CO2, then fastest as the tie-breaker.
    options.sort(
        key=lambda o: (o["co2_emitted_kg"], o["duration_seconds"] or float("inf"))
    )

    # Recommend the lowest-carbon option that is actually viable.
    recommended_mode = None
    for option in options:
        if option["viable"]:
            recommended_mode = option["mode"]
            break
    for option in options:
        option["recommended"] = option["mode"] == recommended_mode

    return {
        "options": options,
        "baseline_co2_kg": baseline_co2,
        "recommended_mode": recommended_mode,
    }
