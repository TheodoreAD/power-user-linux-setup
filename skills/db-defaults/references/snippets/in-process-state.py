"""No install — stdlib only.

threading.Lock + time.monotonic for ephemeral, restart-doesn't-matter state (rate limiters,
counters). A library would be pure overhead for "hold one number, guarded by one lock."
"""

import threading
import time


class RateLimiter:
    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval: float = min_interval_seconds
        self._last_at: float = 0.0
        self._lock: threading.Lock = threading.Lock()

    def throttle(self) -> None:
        with self._lock:
            remaining: float = self._min_interval - (time.monotonic() - self._last_at)
            if remaining > 0:
                time.sleep(remaining)
            self._last_at = time.monotonic()


def test_rate_limiter_enforces_minimum_interval() -> None:
    limiter = RateLimiter(min_interval_seconds=0.01)
    limiter.throttle()
    start = time.monotonic()
    limiter.throttle()
    assert time.monotonic() - start >= 0.01
