"""Central configuration and emission factors for GreenRoute.

ALL carbon factors live in this single file on purpose: it is the one place
an auditor (or a README reader) needs to look to verify the numbers. Nothing
in this project invents its own factor inline -- every gram of CO2 is traced
back to a constant defined here, with its source cited in a comment.

Carbon math is deterministic. The Gemini LLM is used ONLY to phrase a tip in
natural language; it never produces or alters any number.
"""

import os

# ---------------------------------------------------------------------------
# Commute emission factors (kg CO2 per kilometre)
# ---------------------------------------------------------------------------
# Source / assumptions (see README "Assumptions"):
#   - Car: average petrol passenger car, tank-to-wheel.
#   - Bus/transit: average occupancy public bus, per passenger-km.
#   - Walking / cycling: zero operational tailpipe emissions.
COMMUTE_EMISSION_FACTORS = {
    "driving": 0.192,   # kg CO2 / km  (average petrol car)
    "transit": 0.105,   # kg CO2 / km  (average bus / public transit)
    "walking": 0.0,     # kg CO2 / km
    "cycling": 0.0,     # kg CO2 / km
}

# The mode used as the baseline for "CO2 saved vs driving" comparisons.
BASELINE_MODE = "driving"

# Google Maps Routes API travel-mode enum for each of our internal modes.
MAPS_TRAVEL_MODES = {
    "driving": "DRIVE",
    "transit": "TRANSIT",
    "walking": "WALK",
    "cycling": "BICYCLE",
}

# Viability thresholds (km). Used to pick the lowest-carbon *viable* option:
# a zero-carbon mode is only recommended when the trip distance is realistic
# for it. These thresholds are assumptions, documented in the README.
VIABILITY_MAX_KM = {
    "walking": 3.0,    # walking recommended only up to 3 km
    "cycling": 10.0,   # cycling recommended only up to 10 km
    "transit": None,   # viable whenever a transit route exists
    "driving": None,   # always viable when a route exists
}

# ---------------------------------------------------------------------------
# Home-appliance estimator factors
# ---------------------------------------------------------------------------
# Grid electricity emission factor (kg CO2 per kWh).
# Source: CEA CO2 Baseline Database, Version 21.0 (Nov 2025), FY 2024-25,
# weighted average = 0.710 tCO2/MWh = 0.71 kg CO2/kWh.
GRID_EMISSION_FACTOR = 0.71  # kg CO2 / kWh

# Appliance power / energy table. Standard BEE-rating ballpark figures.
# "input" names the single usage value the UI asks for, for that appliance.
#   - power_kw            -> energy = power_kw * (time in hours)
#   - fixed_kwh_per_day   -> energy is fixed regardless of "hours" (fridge)
#   - kwh_per_load        -> energy per ~1-hour wash load
APPLIANCES = {
    "ac": {
        "label": "AC (1.5 ton, 3-star split)",
        "input": "hours_per_day",
        "power_kw": 1.5,
    },
    "refrigerator": {
        "label": "Refrigerator",
        "input": "size",  # always on; ask size, not hours
        "fixed_kwh_per_day": {"small": 0.8, "medium": 1.2, "large": 1.8},
    },
    "washing_machine": {
        "label": "Washing machine",
        "input": "loads_per_week",
        "kwh_per_load": 0.5,  # ~1 hour at 0.5 kW
    },
    "tv": {
        "label": "TV (LED 32-43 inch)",
        "input": "hours_per_day",
        "power_kw": 0.1,
    },
    "ceiling_fan": {
        "label": "Ceiling fan",
        "input": "hours_per_day",
        "power_kw": 0.075,
    },
    "geyser": {
        "label": "Geyser / water heater",
        "input": "minutes_per_day",
        "power_kw": 2.0,
    },
    "microwave": {
        "label": "Microwave",
        "input": "minutes_per_day",
        "power_kw": 1.2,
    },
    "led_bulb": {
        "label": "LED bulb",
        "input": "hours_per_day_x_count",
        "power_kw": 0.01,  # per bulb
    },
}

# Days in a week, used to extrapolate a "typical day" estimate to a week.
DAYS_PER_WEEK = 7

# ---------------------------------------------------------------------------
# Runtime configuration (all secrets come from environment variables)
# ---------------------------------------------------------------------------
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "greenroute_logs")

# Comma-separated list of origins allowed to call the backend (CORS).
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    if o.strip()
]

# Rate limit for the comparison endpoint: max requests per window, per IP.
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))
