"""Logging endpoints -- persist a user's selection to Firestore.

POST /api/log/commute   -> log a chosen commute mode.
POST /api/log/appliance -> log a typical-day appliance estimate.

Both write to the same collection with a distinguishing ``category`` field.

Security note: commute CO2 values are ALWAYS recomputed server-side from the
submitted mode and distance; client-supplied CO2 figures are never trusted or
written to the database. This mirrors the appliance endpoint which also
recomputes from first principles.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.appliances import appliance_daily_co2, appliance_daily_kwh, appliance_weekly_co2
from core.carbon import co2_for_mode, co2_saved_vs_baseline
from core.config import APPLIANCES, COMMUTE_EMISSION_FACTORS
from core.validation import clean_location
from deps import rate_limit
from services import firestore_client

logger = logging.getLogger(__name__)
router = APIRouter()


class CommuteLog(BaseModel):
    start: str
    destination: str
    mode: str
    # distance_km is capped at 2000 km -- enough for any realistic single trip.
    # No upper bound on the original model meant a malicious client could write
    # arbitrarily large CO2 entries; the cap keeps stored values sane.
    distance_km: float = Field(..., ge=0, le=2000)
    # Opaque anonymous browser session identifier (UUID from localStorage).
    # Never a credential: zero auth, just a filter key so stats are per-browser.
    session_id: str = Field("", max_length=64)


class ApplianceLog(BaseModel):
    appliance: str
    params: dict = Field(default_factory=dict)
    session_id: str = Field("", max_length=64)


@router.post(
    "/api/log/commute",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit)],
)
def log_commute(payload: CommuteLog) -> dict:
    """Validate, recompute CO2 server-side, and persist a commute selection.

    The client's CO2 figures are intentionally NOT used: the server recomputes
    from the authoritative emission factors so a tampered request cannot inflate
    the weekly total. Only mode and distance_km are trusted as inputs.
    """
    if payload.mode not in COMMUTE_EMISSION_FACTORS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown mode")
    try:
        start = clean_location(payload.start, "start")
        destination = clean_location(payload.destination, "destination")
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Server-side recomputation -- never trust client-submitted CO2 values.
    co2_emitted = co2_for_mode(payload.distance_km, payload.mode)
    driving_co2 = co2_for_mode(payload.distance_km, "driving")
    co2_saved = co2_saved_vs_baseline(co2_emitted, driving_co2)

    entry = {
        "start": start,
        "destination": destination,
        "mode": payload.mode,
        "distance_km": payload.distance_km,
        "co2_emitted": co2_emitted,
        "co2_saved_vs_driving": co2_saved,
        "session_id": payload.session_id,
    }

    try:
        firestore_client.log_commute(entry)
    except Exception as exc:  # noqa: BLE001 - never leak internals
        logger.error("Firestore commute write failed: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save your selection right now.",
        )
    return {"status": "logged", "category": "commute"}


@router.post(
    "/api/log/appliance",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit)],
)
def log_appliance(payload: ApplianceLog) -> dict:
    """Recompute the appliance CO2 server-side, then persist it.

    The client's numbers are never trusted: the server recomputes from the
    appliance key and usage params so a tampered payload cannot inflate the
    weekly total.
    """
    if payload.appliance not in APPLIANCES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown appliance")
    try:
        entry = {
            "appliance": payload.appliance,
            "usage": payload.params,
            "daily_kwh": round(appliance_daily_kwh(payload.appliance, payload.params), 4),
            "co2_emitted": appliance_daily_co2(payload.appliance, payload.params),
            "co2_emitted_weekly": appliance_weekly_co2(payload.appliance, payload.params),
            "session_id": payload.session_id,
        }
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        firestore_client.log_appliance(entry)
    except Exception as exc:  # noqa: BLE001
        logger.error("Firestore appliance write failed: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save your estimate right now.",
        )
    return {"status": "logged", "category": "appliance"}
