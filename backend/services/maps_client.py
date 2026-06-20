"""Google Maps Routes API client.

Single responsibility: given a start and destination, return raw distance and
duration for each travel mode. It does no carbon math -- that is the job of
``core.carbon``. All failures are caught and surfaced as ``None`` for the
affected mode so a single bad mode never crashes the whole comparison.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

import requests

from core.config import GOOGLE_MAPS_API_KEY, MAPS_TRAVEL_MODES

logger = logging.getLogger(__name__)

_ROUTES_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
_TIMEOUT_SECONDS = 10


class MapsConfigError(RuntimeError):
    """Raised when the Maps API key is not configured."""


def _parse_duration(raw: Optional[str]) -> Optional[int]:
    """Parse a Routes API duration string like ``"1234s"`` into seconds."""
    if not raw:
        return None
    try:
        return int(str(raw).rstrip("s"))
    except ValueError:
        return None


def fetch_route(start: str, destination: str, mode: str) -> Optional[dict]:
    """Fetch one route. Returns ``{distance_meters, duration_seconds}`` or None.

    Returns ``None`` (rather than raising) when no route exists for that mode
    or the API call fails, so the caller can simply omit that option.
    """
    if not GOOGLE_MAPS_API_KEY:
        raise MapsConfigError("GOOGLE_MAPS_API_KEY is not configured")

    travel_mode = MAPS_TRAVEL_MODES[mode]
    body = {
        "origin": {"address": start},
        "destination": {"address": destination},
        "travelMode": travel_mode,
    }
    # Traffic awareness is only valid for driving routes.
    if travel_mode == "DRIVE":
        body["routingPreference"] = "TRAFFIC_AWARE"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.distanceMeters,routes.duration",
    }

    try:
        response = requests.post(
            _ROUTES_ENDPOINT, json=body, headers=headers, timeout=_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        # Log internally; never leak provider error details to the user.
        logger.warning("Maps API call failed for mode=%s: %s", mode, exc)
        return None

    routes = payload.get("routes") or []
    if not routes:
        return None

    first = routes[0]
    distance_meters = first.get("distanceMeters")
    if distance_meters is None:
        return None

    return {
        "distance_meters": distance_meters,
        "duration_seconds": _parse_duration(first.get("duration")),
    }


def fetch_all_routes(start: str, destination: str) -> Dict[str, Optional[dict]]:
    """Fetch routes for every supported mode, concurrently.

    The four per-mode calls are independent, so they run in parallel threads
    (the work is network-bound, not CPU-bound). This keeps a comparison to
    roughly one round-trip of latency instead of four sequential ones.
    Missing modes map to ``None``.
    """
    modes = list(MAPS_TRAVEL_MODES)
    with ThreadPoolExecutor(max_workers=len(modes)) as pool:
        results = pool.map(lambda m: (m, fetch_route(start, destination, m)), modes)
        return dict(results)
