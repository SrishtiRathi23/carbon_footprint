"""Logging endpoints -- persist a user's selection to Firestore.

POST /api/log/commute   -> log a chosen commute mode.
POST /api/log/appliance -> log a typical-day appliance estimate.

Both write to the same collection with a distinguishing ``category`` field.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.appliances import appliance_daily_co2, appliance_daily_kwh, appliance_weekly_co2
from core.config import APPLIANCES, COMMUTE_EMISSION_FACTORS
from core.validation import clean_location
from services import firestore_client

logger = logging.getLogger(__name__)
router = APIRouter()


class CommuteLog(BaseModel):
    start: str
    destination: str
    mode: str
    distance_km: float = Field(..., ge=0)
    co2_emitted: float = Field(..., ge=0)
    co2_saved_vs_driving: float = Field(..., ge=0)


class ApplianceLog(BaseModel):
    appliance: str
    params: dict = Field(default_factory=dict)


@router.post("/api/log/commute", status_code=status.HTTP_201_CREATED)
def log_commute(payload: CommuteLog) -> dict:
    """Validate and persist a commute selection."""
    if payload.mode not in COMMUTE_EMISSION_FACTORS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown mode")
    try:
        entry = {
            "start": clean_location(payload.start, "start"),
            "destination": clean_location(payload.destination, "destination"),
            "mode": payload.mode,
            "distance_km": payload.distance_km,
            "co2_emitted": payload.co2_emitted,
            "co2_saved_vs_driving": payload.co2_saved_vs_driving,
        }
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        firestore_client.log_commute(entry)
    except Exception as exc:  # noqa: BLE001 - never leak internals
        logger.error("Firestore commute write failed: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save your selection right now.",
        )
    return {"status": "logged", "category": "commute"}


@router.post("/api/log/appliance", status_code=status.HTTP_201_CREATED)
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
