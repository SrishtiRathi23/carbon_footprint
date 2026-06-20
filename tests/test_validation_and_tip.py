"""Unit tests for input sanitization and the Gemini fallback tip.

These cover the security boundary (what reaches an external API) and the
graceful-degradation path (what happens when Gemini is unavailable).
"""

import pytest

from core.validation import MAX_LOCATION_LENGTH, clean_location
from services.gemini_client import _fallback_tip


def test_clean_location_strips_control_and_disallowed_chars():
    cleaned = clean_location("  India\x00 Gate<script>  ", "destination")
    # Control char and angle brackets removed, whitespace collapsed.
    assert cleaned == "India Gatescript"


def test_clean_location_keeps_address_punctuation():
    assert clean_location("A-14, Sector 125, Noida", "start") == "A-14, Sector 125, Noida"


def test_clean_location_rejects_empty():
    with pytest.raises(ValueError):
        clean_location("   ", "start")


def test_clean_location_rejects_too_long():
    with pytest.raises(ValueError):
        clean_location("x" * (MAX_LOCATION_LENGTH + 1), "start")


def test_clean_location_rejects_non_string():
    with pytest.raises(ValueError):
        clean_location(None, "destination")


def test_fallback_tip_uses_real_numbers():
    comparison = {
        "options": [
            {"mode": "walking", "co2_emitted_kg": 0.0,
             "co2_saved_vs_driving_kg": 1.04, "recommended": True},
            {"mode": "driving", "co2_emitted_kg": 1.04,
             "co2_saved_vs_driving_kg": 0.0, "recommended": False},
        ]
    }
    tip = _fallback_tip(comparison)
    assert "walking" in tip
    assert "1.04" in tip


def test_fallback_tip_handles_no_recommendation():
    tip = _fallback_tip({"options": []})
    assert "No viable route" in tip
