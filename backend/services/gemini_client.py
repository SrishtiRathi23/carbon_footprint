"""Gemini client -- natural-language explanation and follow-up answers.

Strict scope: Gemini turns numbers the code ALREADY computed into readable
language. It never computes carbon and never decides the recommendation.
Two uses:
  * generate_tip(comparison)        -> a detailed multi-sentence insight
  * answer_followup(question, ctx)  -> answers a user's follow-up question,
                                       grounded in the same numbers

Every function degrades gracefully: if the API key is missing or a call
fails, a deterministic local fallback is returned so the rest of the app is
unaffected.

Efficiency note: the GenerativeModel instance is created once per process
(lazy singleton, same pattern as the Firestore client) rather than on every
request, so ``genai.configure()`` and ``genai.GenerativeModel()`` are called
at most once regardless of traffic.
"""

import logging

from core.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# Module-level singleton -- created once on first use, never recreated.
# None means either the key is missing or initialisation failed.
_gemini_model = None


def _get_model():
    """Return the cached Gemini GenerativeModel, initialising it once if needed.

    Returns ``None`` when the API key is absent or the SDK fails to import,
    so callers can fall back to a deterministic tip without raising.
    """
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    if not GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL)
        return _gemini_model
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini init failed: %s", exc)
        return None


def _fallback_tip(comparison: dict) -> str:
    """Deterministic, number-accurate insight used when Gemini is unavailable."""
    options = comparison.get("options", [])
    recommended = next((o for o in options if o.get("recommended")), None)
    if not recommended:
        return "No viable route was found for this trip, so no recommendation can be made."

    mode = recommended["mode"]
    saved = recommended["co2_saved_vs_driving_kg"]
    distance = recommended.get("distance_km")
    trip = f"{distance} km " if distance is not None else ""
    driving = next((o for o in options if o["mode"] == "driving"), None)
    driving_co2 = driving["co2_emitted_kg"] if driving else 0.0

    if saved > 0:
        return (
            f"For this {trip}trip, {mode} is the greenest viable option, "
            f"emitting {recommended['co2_emitted_kg']} kg CO2 versus {driving_co2} kg "
            f"for driving. Choosing it saves about {saved} kg CO2. Over a year of "
            f"daily trips that adds up to a meaningful reduction in your footprint."
        )
    return (
        f"Driving is the only viable option for this {trip}trip, "
        f"emitting {recommended['co2_emitted_kg']} kg CO2."
    )


def _data_block(comparison: dict) -> str:
    """Render the computed numbers as plain text for grounding the prompt.

    Uses defensive ``.get`` access so a partial or malformed payload can never
    raise (and therefore never produce a 500).
    """
    lines = []
    for option in comparison.get("options", []):
        if not isinstance(option, dict):
            continue
        tag = " (recommended)" if option.get("recommended") else ""
        lines.append(
            f"- {option.get('mode', 'unknown')}{tag}: "
            f"{option.get('distance_km', 'n/a')} km, "
            f"{option.get('duration_seconds') or 'n/a'} s, "
            f"{option.get('co2_emitted_kg', 'n/a')} kg CO2, "
            f"saves {option.get('co2_saved_vs_driving_kg', 'n/a')} kg vs driving"
        )
    return "\n".join(lines)


def generate_tip(comparison: dict) -> str:
    """Return a detailed factual insight (2-4 sentences) for a comparison.

    Always returns a usable string -- never raises -- so a Gemini outage can
    never break the comparison endpoint.
    """
    model = _get_model()
    if model is None:
        return _fallback_tip(comparison)

    prompt = (
        "You are a carbon-footprint assistant. Using ONLY the data below, write "
        "2 to 4 short sentences for the user. Name the recommended option, state "
        "its CO2 and the kg saved versus driving using the real numbers, briefly "
        "note the time trade-off if relevant, and end with one practical takeaway. "
        "Do not invent data. No emojis. Plain text.\n\nData:\n"
        + _data_block(comparison)
    )
    try:
        response = model.generate_content(prompt)
        text = (getattr(response, "text", "") or "").strip()
        return text or _fallback_tip(comparison)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini insight generation failed: %s", exc)
        return _fallback_tip(comparison)


def answer_followup(question: str, comparison: dict) -> str:
    """Answer a user's follow-up question grounded in the comparison numbers."""
    model = _get_model()
    if model is None:
        return (
            "The assistant is unavailable right now, but you can compare the "
            "options above: the greenest viable choice is highlighted as "
            "Recommended, with the exact CO2 saved versus driving shown on each card."
        )

    prompt = (
        "You are a helpful, factual carbon-footprint assistant. Answer the user's "
        "question in 2 to 4 sentences. Use the route data below where relevant and "
        "do NOT invent numbers. If the question is unrelated to commuting, carbon, "
        "or this trip, give a brief general but accurate answer. No emojis.\n\n"
        "Route data:\n" + _data_block(comparison) + f"\n\nQuestion: {question}"
    )
    try:
        response = model.generate_content(prompt)
        text = (getattr(response, "text", "") or "").strip()
        return text or "Sorry, I could not generate an answer for that. Please try rephrasing."
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini follow-up failed: %s", exc)
        return "Sorry, the assistant could not answer that right now. Please try again shortly."
