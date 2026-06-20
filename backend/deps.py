"""Shared FastAPI dependencies (rate limiting).

Kept separate so route modules can import the limiter without importing the
app, avoiding circular imports.
"""

from fastapi import HTTPException, Request, status

from core.config import RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
from core.rate_limit import RateLimiter

_limiter = RateLimiter(RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)


def rate_limit(request: Request) -> None:
    """Reject the request if the caller IP exceeds the configured limit."""
    client = request.client.host if request.client else "unknown"
    if not _limiter.allow(client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down and try again shortly.",
        )
