"""Tier-based scan scheduling."""

from __future__ import annotations

import time

from config.settings import Settings, get_settings


class TierScheduler:
    """Track per-tier last scan times and return tiers due for a scan."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._intervals: dict[int, int] = {
            1: self._settings.filter_tier1_interval_seconds,
            2: self._settings.filter_tier2_interval_seconds,
            3: self._settings.filter_tier3_interval_seconds,
        }
        self._last_scan: dict[int, float] = {}

    def get_due_tiers(self, *, now: float | None = None) -> list[int]:
        """Return tier numbers that have exceeded their scan interval.

        A tier with no prior scan is always due.
        """
        clock = now if now is not None else time.monotonic()
        due: list[int] = []
        for tier, interval in sorted(self._intervals.items()):
            last = self._last_scan.get(tier)
            if last is None or (clock - last) >= interval:
                due.append(tier)
        return due

    def mark_scanned(self, tier: int, *, now: float | None = None) -> None:
        """Record that *tier* was scanned at *now*."""
        self._last_scan[tier] = now if now is not None else time.monotonic()

    def last_scan_monotonic(self, tier: int) -> float | None:
        """Return monotonic timestamp of the last scan for *tier*, if any."""
        return self._last_scan.get(tier)
