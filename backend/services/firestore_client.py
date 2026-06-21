"""Firestore access layer.

Single responsibility: persist trip/appliance logs and aggregate the current
week's totals. The Firestore client is created lazily so importing this module
(e.g. during unit tests) never requires real credentials. All persisted
documents share one collection and are distinguished by a ``category`` field
("commute" or "appliance").

Session isolation: every document stores an opaque ``session_id`` (a
client-generated UUID from localStorage) so that the weekly stats query can
be filtered per-browser. This requires no credentials or auth middleware --
the ID is purely an opaque filter key.
"""

import datetime as _dt
import logging
from typing import Optional

from core.config import FIRESTORE_COLLECTION, GCP_PROJECT_ID

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """Return a cached Firestore client, creating it on first use."""
    global _client
    if _client is None:
        from google.cloud import firestore

        _client = (
            firestore.Client(project=GCP_PROJECT_ID)
            if GCP_PROJECT_ID
            else firestore.Client()
        )
    return _client


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _week_start(now: Optional[_dt.datetime] = None) -> _dt.datetime:
    """Start (Monday 00:00 UTC) of the week containing ``now``."""
    now = now or _utcnow()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight - _dt.timedelta(days=now.weekday())


def log_commute(entry: dict, client=None) -> dict:
    """Persist a commute selection and return the stored document.

    Stores exactly the fields the spec requires plus bookkeeping fields.
    The ``session_id`` in ``entry`` is an opaque anonymous browser identifier
    used only to filter per-browser weekly stats -- not a credential.
    """
    client = client or get_client()
    document = {
        "category": "commute",
        "date": _utcnow().isoformat(),
        "start": entry["start"],
        "destination": entry["destination"],
        "mode": entry["mode"],
        "distance_km": entry["distance_km"],
        "co2_emitted": entry["co2_emitted"],
        "co2_saved_vs_driving": entry["co2_saved_vs_driving"],
        "session_id": entry.get("session_id", ""),
        "created_at": _utcnow(),
    }
    client.collection(FIRESTORE_COLLECTION).add(document)
    return document


def log_appliance(entry: dict, client=None) -> dict:
    """Persist an appliance estimate (typical-day) and return the document."""
    client = client or get_client()
    document = {
        "category": "appliance",
        "date": _utcnow().isoformat(),
        "appliance": entry["appliance"],
        "usage": entry["usage"],
        "daily_kwh": entry["daily_kwh"],
        "co2_emitted": entry["co2_emitted"],          # daily kg CO2
        "co2_emitted_weekly": entry["co2_emitted_weekly"],
        "session_id": entry.get("session_id", ""),
        "created_at": _utcnow(),
    }
    client.collection(FIRESTORE_COLLECTION).add(document)
    return document


def weekly_totals(
    client=None,
    now: Optional[_dt.datetime] = None,
    session_id: str = "",
) -> dict:
    """Aggregate this week's logs into one combined figure plus a breakdown.

    - commute_co2_saved_kg     : sum of co2_saved_vs_driving for commute logs.
    - appliance_co2_emitted_kg : sum of weekly appliance emissions.
    - combined_co2_kg : commute savings + appliance emissions this week.

    If ``session_id`` is provided (non-empty), only documents belonging to
    that anonymous browser session are included, giving per-browser totals
    without any login or credentials.  When omitted, all documents are
    counted (used by tests and the health check).

    Production note: the (session_id, created_at) query requires a composite
    Firestore index defined in ``firestore.indexes.json``.
    """
    client = client or get_client()
    start = _week_start(now)

    commute_saved = 0.0
    appliance_emitted = 0.0
    count = 0

    query = client.collection(FIRESTORE_COLLECTION).where("created_at", ">=", start)
    if session_id:
        query = query.where("session_id", "==", session_id)

    for snapshot in query.stream():
        data = snapshot.to_dict() or {}
        count += 1
        if data.get("category") == "commute":
            commute_saved += float(data.get("co2_saved_vs_driving", 0) or 0)
        elif data.get("category") == "appliance":
            appliance_emitted += float(data.get("co2_emitted_weekly", 0) or 0)

    return {
        "week_start": start.isoformat(),
        "commute_co2_saved_kg": round(commute_saved, 3),
        "appliance_co2_emitted_kg": round(appliance_emitted, 3),
        "combined_co2_kg": round(commute_saved + appliance_emitted, 3),
        "entries_this_week": count,
    }
