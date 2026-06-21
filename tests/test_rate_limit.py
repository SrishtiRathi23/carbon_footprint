"""Unit tests for the in-memory fixed-window rate limiter.

Covers:
- Requests within the limit are allowed.
- Requests over the limit are denied.
- Different keys (IPs) are tracked independently.
- The limiter is thread-safe under concurrent load.
"""

import threading

import pytest

from core.rate_limit import RateLimiter


def test_requests_under_limit_are_allowed():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.allow("ip-1") is True
    assert limiter.allow("ip-1") is True
    assert limiter.allow("ip-1") is True


def test_requests_over_limit_are_denied():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    limiter.allow("ip-2")
    limiter.allow("ip-2")
    limiter.allow("ip-2")
    # Fourth request in the same window must be denied.
    assert limiter.allow("ip-2") is False


def test_different_keys_are_tracked_independently():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    # First request for each key succeeds.
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-b") is True
    # Second request for client-a is denied; client-b unaffected.
    assert limiter.allow("client-a") is False
    # client-b's second request is also denied.
    assert limiter.allow("client-b") is False


def test_thread_safe_under_concurrent_calls():
    """Exactly max_requests threads should be allowed and the rest denied,
    with no data race in the internal counter.
    """
    max_req = 10
    total = 20
    limiter = RateLimiter(max_requests=max_req, window_seconds=60)
    results = []
    lock = threading.Lock()

    def make_request():
        result = limiter.allow("shared-ip")
        with lock:
            results.append(result)

    threads = [threading.Thread(target=make_request) for _ in range(total)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    allowed = sum(1 for r in results if r)
    denied = sum(1 for r in results if not r)
    assert allowed == max_req, f"Expected {max_req} allowed, got {allowed}"
    assert denied == total - max_req, f"Expected {total - max_req} denied, got {denied}"
