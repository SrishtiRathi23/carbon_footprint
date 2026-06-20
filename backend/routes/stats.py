"""Weekly statistics endpoint.

GET /api/stats/weekly -> combined CO2 figure for the current week across both
commute savings and appliance emissions, plus the breakdown.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from services import firestore_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/stats/weekly")
def weekly_stats() -> dict:
    """Return this week's combined CO2 total and its breakdown."""
    try:
        return firestore_client.weekly_totals()
    except Exception as exc:  # noqa: BLE001 - never leak internals
        logger.error("Weekly aggregation failed: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load weekly stats right now.",
        )
