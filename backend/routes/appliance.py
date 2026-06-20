"""Home-appliance estimator endpoints.

GET  /api/appliances          -> metadata so the frontend can build the form.
POST /api/appliances/estimate -> deterministic daily/weekly CO2 for one entry.

No external API calls here -- the math is pure and unit-tested.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.appliances import appliance_daily_co2, appliance_daily_kwh, appliance_weekly_co2
from core.config import APPLIANCES

router = APIRouter()


class EstimateRequest(BaseModel):
    appliance: str = Field(..., description="Appliance key, e.g. 'ac'")
    params: dict = Field(default_factory=dict, description="Usage values")


@router.get("/api/appliances")
def list_appliances() -> dict:
    """Expose the appliance catalogue (key, label, expected input)."""
    return {
        "appliances": [
            {"key": key, "label": spec["label"], "input": spec["input"]}
            for key, spec in APPLIANCES.items()
        ]
    }


@router.post("/api/appliances/estimate")
def estimate(payload: EstimateRequest) -> dict:
    """Compute daily kWh, daily CO2 and weekly CO2 for one appliance entry."""
    try:
        daily_kwh = round(appliance_daily_kwh(payload.appliance, payload.params), 4)
        daily_co2 = appliance_daily_co2(payload.appliance, payload.params)
        weekly_co2 = appliance_weekly_co2(payload.appliance, payload.params)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {
        "appliance": payload.appliance,
        "label": APPLIANCES[payload.appliance]["label"],
        "daily_kwh": daily_kwh,
        "co2_emitted_kg": daily_co2,
        "co2_emitted_weekly_kg": weekly_co2,
    }
