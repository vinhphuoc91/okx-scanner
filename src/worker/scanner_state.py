"""Redis-backed scanner worker status (shared with the API)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import redis as redis_lib

from config import settings
from src.utils.logger import get_logger

log = get_logger(__name__)

_KEY_PREFIX = "okx:scanner"
_HEARTBEAT_STALE_SECONDS = 120


class ScannerState:
    """Read/write scanner lifecycle metadata in Redis."""

    def __init__(self, *, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or settings.redis_url

    def _client(self) -> redis_lib.Redis:
        return redis_lib.from_url(
            self._redis_url,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_timeout,
            decode_responses=True,
        )

    def mark_running(self, started_at: datetime) -> None:
        """Record worker start."""
        client = self._client()
        try:
            client.set(f"{_KEY_PREFIX}:running", "1")
            client.set(f"{_KEY_PREFIX}:started_at", started_at.isoformat())
            client.set(f"{_KEY_PREFIX}:heartbeat", started_at.isoformat())
        finally:
            client.close()

    def heartbeat(self) -> None:
        """Refresh liveness timestamp."""
        client = self._client()
        try:
            client.set(f"{_KEY_PREFIX}:heartbeat", datetime.now(tz=UTC).isoformat())
        finally:
            client.close()

    def mark_stopped(self) -> None:
        """Record worker shutdown."""
        client = self._client()
        try:
            client.set(f"{_KEY_PREFIX}:running", "0")
        finally:
            client.close()

    def set_tier_scan(self, tier: int, scanned_at: datetime) -> None:
        """Persist last successful scan time for *tier*."""
        client = self._client()
        try:
            client.set(f"{_KEY_PREFIX}:tier:{tier}:last_scan", scanned_at.isoformat())
        finally:
            client.close()

    def update_cycle_stats(self, stats: dict[str, int]) -> None:
        """Increment cumulative counters stored in Redis."""
        client = self._client()
        try:
            pipe = client.pipeline()
            for key, delta in stats.items():
                pipe.hincrby(f"{_KEY_PREFIX}:totals", key, delta)
            pipe.execute()
        finally:
            client.close()

    def get_status(self) -> dict[str, Any]:
        """Return scanner status snapshot for API / health checks."""
        client = self._client()
        try:
            running = client.get(f"{_KEY_PREFIX}:running") == "1"
            started_at_raw = client.get(f"{_KEY_PREFIX}:started_at")
            heartbeat_raw = client.get(f"{_KEY_PREFIX}:heartbeat")
            totals = client.hgetall(f"{_KEY_PREFIX}:totals") or {}

            tier_scans: dict[str, str | None] = {}
            for tier in (1, 2, 3):
                tier_scans[str(tier)] = client.get(f"{_KEY_PREFIX}:tier:{tier}:last_scan")

            started_at = _parse_iso(started_at_raw)
            heartbeat = _parse_iso(heartbeat_raw)
            uptime_seconds: float | None = None
            if started_at is not None:
                uptime_seconds = (datetime.now(tz=UTC) - started_at).total_seconds()

            stale = False
            if heartbeat is not None:
                stale = (datetime.now(tz=UTC) - heartbeat).total_seconds() > _HEARTBEAT_STALE_SECONDS
            elif running:
                stale = True

            return {
                "running": running and not stale,
                "started_at": started_at_raw,
                "heartbeat_at": heartbeat_raw,
                "uptime_seconds": uptime_seconds,
                "last_scan_by_tier": tier_scans,
                "totals": {k: int(v) for k, v in totals.items()},
                "stale": stale,
            }
        finally:
            client.close()

    def check_health(self) -> tuple[str, str | None]:
        """Return ``(status, detail)`` for the health endpoint."""
        status = self.get_status()
        if not status["running"]:
            return "down", "worker not running"
        if status["stale"]:
            return "degraded", "heartbeat stale"
        return "ok", None


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
