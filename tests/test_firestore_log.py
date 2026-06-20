"""Unit tests for Firestore logging.

The real Firestore client is never used: a fake client captures whatever the
code tries to persist, so we can assert the exact fields written without any
network or credentials.
"""

from services import firestore_client


class FakeCollection:
    def __init__(self, sink):
        self._sink = sink

    def add(self, document):
        self._sink.append(document)
        return ("doc-id", None)


class FakeClient:
    def __init__(self):
        self.documents = []

    def collection(self, name):
        self.captured_collection = name
        return FakeCollection(self.documents)


def test_log_commute_writes_expected_fields():
    fake = FakeClient()
    entry = {
        "start": "A Street",
        "destination": "B Avenue",
        "mode": "cycling",
        "distance_km": 4.9,
        "co2_emitted": 0.0,
        "co2_saved_vs_driving": 0.94,
    }
    firestore_client.log_commute(entry, client=fake)

    assert len(fake.documents) == 1
    doc = fake.documents[0]
    # Exactly the fields the spec requires must be present.
    for field in (
        "category",
        "date",
        "start",
        "destination",
        "mode",
        "distance_km",
        "co2_emitted",
        "co2_saved_vs_driving",
    ):
        assert field in doc
    assert doc["category"] == "commute"
    assert doc["mode"] == "cycling"
    assert doc["co2_saved_vs_driving"] == 0.94


def test_log_appliance_writes_category_and_carbon():
    fake = FakeClient()
    entry = {
        "appliance": "ac",
        "usage": {"hours_per_day": 6},
        "daily_kwh": 9.0,
        "co2_emitted": 6.39,
        "co2_emitted_weekly": 44.73,
    }
    firestore_client.log_appliance(entry, client=fake)

    doc = fake.documents[0]
    assert doc["category"] == "appliance"
    assert doc["appliance"] == "ac"
    assert doc["co2_emitted_weekly"] == 44.73


def test_weekly_totals_combines_both_categories():
    """weekly_totals must sum commute savings and appliance emissions."""
    import datetime as dt

    now = dt.datetime(2026, 6, 17, 12, 0, tzinfo=dt.timezone.utc)  # a Wednesday

    class StreamingClient:
        def collection(self, name):
            return self

        def where(self, *args, **kwargs):
            return self

        def stream(self):
            class Snap:
                def __init__(self, data):
                    self._data = data

                def to_dict(self):
                    return self._data

            return iter(
                [
                    Snap({"category": "commute", "co2_saved_vs_driving": 0.94}),
                    Snap({"category": "commute", "co2_saved_vs_driving": 1.06}),
                    Snap({"category": "appliance", "co2_emitted_weekly": 44.73}),
                ]
            )

    totals = firestore_client.weekly_totals(client=StreamingClient(), now=now)
    assert totals["commute_co2_saved_kg"] == 2.0
    assert totals["appliance_co2_emitted_kg"] == 44.73
    assert totals["combined_co2_kg"] == 46.73
    assert totals["entries_this_week"] == 3
