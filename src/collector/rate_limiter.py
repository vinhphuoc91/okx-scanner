"""Thread-safe sliding-window rate limiter for OKX REST calls."""

from __future__ import annotations

import threading
import time
from collections import deque


class RateLimiter:
    """Allow at most *max_requests* within a rolling *window_seconds* window."""

    def __init__(self, max_requests: int = 20, window_seconds: float = 2.0) -> None:
        """Initialize the limiter.

        Parameters
        ----------
        max_requests:
            Maximum requests allowed per window (OKX public: 20 / 2 s).
        window_seconds:
            Rolling window length in seconds.
        """
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a request slot is available."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window_seconds
            while self._timestamps and self._timestamps[0] <= cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._max_requests:
                sleep_for = self._window_seconds - (now - self._timestamps[0]) + 0.001
                if sleep_for > 0:
                    time.sleep(sleep_for)
                now = time.monotonic()
                cutoff = now - self._window_seconds
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()

            self._timestamps.append(time.monotonic())
