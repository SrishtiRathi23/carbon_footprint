"""GreenRoute backend application.

FastAPI app that wires together the commute comparator and the home-appliance
estimator. Thin by design: each concern lives in its own module under
``routes/``, ``services/`` and ``core/``. This file only assembles them and
configures cross-cutting middleware (CORS) and a health check.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import ALLOWED_ORIGINS
from routes import appliance, ask, compare, logs, stats

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GreenRoute",
    description="Commute Carbon Comparator + Home Appliance Estimator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(compare.router, tags=["commute"])
app.include_router(appliance.router, tags=["appliance"])
app.include_router(ask.router, tags=["assistant"])
app.include_router(logs.router, tags=["logging"])
app.include_router(stats.router, tags=["stats"])


@app.get("/healthz", tags=["health"])
def health() -> dict:
    """Liveness probe for Cloud Run."""
    return {"status": "ok"}
