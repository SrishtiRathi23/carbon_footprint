"""Deterministic home-appliance carbon math.

Pure functions only -- no network, no I/O. Converts an appliance plus a usage
value into daily kWh, then into kg CO2 using the single grid emission factor
in ``config.py``. Same shape as the commute math: a fixed factor times a
usage number, fully testable.

Model:
    daily_kwh = power_kw * hours          (time-based appliances)
    daily_kwh = fixed_kwh_per_day         (refrigerator, always on)
    daily_kwh = (loads_per_week / 7) * kwh_per_load   (washing machine)
    daily_co2_kg = daily_kwh * GRID_EMISSION_FACTOR

Weekly figures use a "typical day" assumption: the usage entered represents a
normal day, so weekly = daily * 7 (see README "Assumptions").
"""

from .config import APPLIANCES, DAYS_PER_WEEK, GRID_EMISSION_FACTOR


def appliance_daily_kwh(appliance_key: str, params: dict) -> float:
    """Daily energy use (kWh) for one appliance given its usage ``params``.

    ``params`` carries only the field relevant to that appliance:
      - ac / tv / ceiling_fan : {"hours_per_day": float}
      - refrigerator          : {"size": "small"|"medium"|"large"}
      - washing_machine       : {"loads_per_week": float}
      - geyser / microwave    : {"minutes_per_day": float}
      - led_bulb              : {"hours_per_day": float, "count": int}

    Raises ``ValueError`` for unknown appliances or invalid usage so bad
    input can never silently produce a wrong carbon figure.
    """
    if appliance_key not in APPLIANCES:
        raise ValueError(f"Unknown appliance: {appliance_key!r}")

    spec = APPLIANCES[appliance_key]
    input_type = spec["input"]

    if input_type == "size":
        size = str(params.get("size", "")).lower()
        table = spec["fixed_kwh_per_day"]
        if size not in table:
            raise ValueError(f"size must be one of {sorted(table)}")
        return table[size]

    if input_type == "loads_per_week":
        loads = _non_negative(params.get("loads_per_week"), "loads_per_week")
        return (loads / DAYS_PER_WEEK) * spec["kwh_per_load"]

    if input_type == "hours_per_day":
        hours = _non_negative(params.get("hours_per_day"), "hours_per_day")
        return spec["power_kw"] * hours

    if input_type == "minutes_per_day":
        minutes = _non_negative(params.get("minutes_per_day"), "minutes_per_day")
        return spec["power_kw"] * (minutes / 60.0)

    if input_type == "hours_per_day_x_count":
        hours = _non_negative(params.get("hours_per_day"), "hours_per_day")
        count = int(_non_negative(params.get("count", 1), "count"))
        return spec["power_kw"] * hours * count

    # Defensive: a new appliance added to config without a handler here.
    raise ValueError(f"Unsupported input type: {input_type!r}")


def appliance_daily_co2(appliance_key: str, params: dict) -> float:
    """Daily kg CO2 for one appliance, rounded to 3 decimals."""
    return round(appliance_daily_kwh(appliance_key, params) * GRID_EMISSION_FACTOR, 3)


def appliance_weekly_co2(appliance_key: str, params: dict) -> float:
    """Weekly kg CO2 under the typical-day assumption (daily * 7)."""
    return round(appliance_daily_co2(appliance_key, params) * DAYS_PER_WEEK, 3)


def _non_negative(value, name: str) -> float:
    """Validate a numeric usage value is present and >= 0."""
    if value is None:
        raise ValueError(f"{name} is required")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number")
    if number < 0:
        raise ValueError(f"{name} must be non-negative")
    return number
