"""A small in-memory fixed-window rate limiter.

Kept dependency-free on purpose (the spec asks for a lightweight app). It
caps requests per client IP within a time window. This is per-process state;
on a multi-instance Cloud Run deployment each instance limits independently,
which is acceptable for this MVP and noted in the README. For strict global
limiting you would move the counter to Redis/Memorystore.

Memory management: idle keys (no hit in 2× the window) are evicted on each
``allow()`` call so the ``_hits`` dict does not grow without bound when the
server receives traffic from many distinct IPs over time.
"""

import threading
import time
from collections import defaultdict
from typing import Dict, List


class RateLimiter:
    """Allow at most ``max_requests`` per ``window_seconds`` per key (IP)."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record a hit for ``key`` and return whether it is within the limit.

        Also evicts keys that have been completely idle for more than
        2 × window_seconds so memory usage stays bounded even under sustained
        traffic from many distinct IP addresses.
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds
        idle_cutoff = now - (2 * self.window_seconds)

        with self._lock:
            # Evict idle keys whose most-recent hit is older than 2× the window.
            idle_keys = [
                k for k, ts in self._hits.items()
                if not ts or ts[-1] < idle_cutoff
            ]
            for k in idle_keys:
                del self._hits[k]

            # Prune expired hits for the current key and check the limit.
            hits = [t for t in self._hits[key] if t > cutoff]
            if len(hits) >= self.max_requests:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True
