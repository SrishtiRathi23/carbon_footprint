"""Server-side input validation and sanitization.

Every user-supplied string is validated here before it touches an external
API (Maps, Gemini) or the database. The goal is twofold: reject malformed
input early with a clear message, and strip control characters so nothing
weird is forwarded to a third-party service.
"""

import re

# Locations are free text (addresses, place names). Allow letters, digits,
# spaces and ordinary address punctuation; reject everything else.
_LOCATION_ALLOWED = re.compile(r"[^0-9A-Za-z\s,.\-/#&()']")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

MAX_LOCATION_LENGTH = 200


def clean_location(raw: str, field_name: str) -> str:
    """Validate and sanitize a location string.

    Strips control characters and disallowed symbols, collapses whitespace,
    and enforces a length bound. Raises ``ValueError`` if the result is empty
    or too long.
    """
    if raw is None or not isinstance(raw, str):
        raise ValueError(f"{field_name} is required")

    text = _CONTROL_CHARS.sub("", raw)
    text = _LOCATION_ALLOWED.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        raise ValueError(f"{field_name} must not be empty")
    if len(text) > MAX_LOCATION_LENGTH:
        raise ValueError(
            f"{field_name} must be at most {MAX_LOCATION_LENGTH} characters"
        )
    return text
