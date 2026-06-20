"""Unit tests for the deterministic appliance carbon math.

Grid factor = 0.71 kg CO2/kWh. Numbers verified by hand below.
"""

import pytest

from core.appliances import (
    appliance_daily_co2,
    appliance_daily_kwh,
    appliance_weekly_co2,
)


def test_ac_hours():
    # 1.5 kW * 6 h = 9 kWh/day
    assert appliance_daily_kwh("ac", {"hours_per_day": 6}) == 9.0
    # 9 kWh * 0.71 = 6.39 kg/day
    assert appliance_daily_co2("ac", {"hours_per_day": 6}) == 6.39


def test_refrigerator_fixed_by_size():
    assert appliance_daily_kwh("refrigerator", {"size": "small"}) == 0.8
    assert appliance_daily_kwh("refrigerator", {"size": "medium"}) == 1.2
    assert appliance_daily_kwh("refrigerator", {"size": "large"}) == 1.8
    # medium: 1.2 * 0.71 = 0.852 kg/day
    assert appliance_daily_co2("refrigerator", {"size": "medium"}) == 0.852


def test_washing_machine_loads_per_week():
    # 7 loads/week -> 1 load/day -> 0.5 kWh/day
    assert appliance_daily_kwh("washing_machine", {"loads_per_week": 7}) == 0.5


def test_geyser_minutes():
    # 2 kW * (30/60) h = 1 kWh/day
    assert appliance_daily_kwh("geyser", {"minutes_per_day": 30}) == 1.0


def test_led_bulb_count():
    # 0.01 kW * 5 h * 4 bulbs = 0.2 kWh/day
    assert appliance_daily_kwh("led_bulb", {"hours_per_day": 5, "count": 4}) == 0.2


def test_weekly_is_daily_times_seven():
    daily = appliance_daily_co2("ac", {"hours_per_day": 6})
    weekly = appliance_weekly_co2("ac", {"hours_per_day": 6})
    assert weekly == round(daily * 7, 3)


def test_unknown_appliance_raises():
    with pytest.raises(ValueError):
        appliance_daily_kwh("nuclear_reactor", {"hours_per_day": 1})


def test_bad_size_raises():
    with pytest.raises(ValueError):
        appliance_daily_kwh("refrigerator", {"size": "gigantic"})


def test_missing_usage_raises():
    with pytest.raises(ValueError):
        appliance_daily_kwh("ac", {})


def test_negative_usage_raises():
    with pytest.raises(ValueError):
        appliance_daily_kwh("ac", {"hours_per_day": -3})
