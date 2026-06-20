"""Commute comparison endpoint.

POST /api/compare -> for a start/destination, fetch routes for all four modes,
compute deterministic CO2 per mode, sort greenest-first, mark the recommended
viable option, and attach a one-line Gemini tip.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.carbon import build_comparison
from core.validation import clean_location
from deps import rate_limit
from services.gemini_client import generate_tip
from services.maps_client import MapsConfigError, fetch_all_routes

logger = logging.getLogger(__name__)
router = APIRouter()


class CompareRequest(BaseModel):
    start: str = Field(..., description="Start location, free text")
    destination: str = Field(..., description="Destination, free text")


@router.post("/api/compare", dependencies=[Depends(rate_limit)])
def compare(payload: CompareRequest) -> dict:
    """Return sorted, labelled mode options with CO2 and a tip."""
    try:
        start = clean_location(payload.start, "start")
        destination = clean_location(payload.destination, "destination")
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        routes = fetch_all_routes(start, destination)
    except MapsConfigError:
        logger.error("Maps API key missing")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Route service is temporarily unavailable.",
        )

    if not any(routes.values()):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="No routes found for the given locations.",
        )

    comparison = build_comparison(routes)
    comparison["start"] = start
    comparison["destination"] = destination
    comparison["tip"] = generate_tip(comparison)
    return comparison
