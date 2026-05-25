"""Redis-backed cache for normalized market data."""

from __future__ import annotations

import json
from typing import Any

import redis
from redis.exceptions import RedisError

from config import settings
from src.schemas.market import (
    NormalizedCandle,
    NormalizedFundingRate,
    NormalizedTicker,
)
from src.utils.logger import get_logger

log = get_logger(__name__)

# TTL strategy (seconds)
TTL_TICKER = 30
TTL_CANDLE_5M = 300
TTL_CANDLE_15M = 900
TTL_CANDLE_1H = 3600
TTL_FUNDING_RATE = 28_800
TTL_INSTRUMENTS = 86_400

_CANDLE_TTL: dict[str, int] = {
    "5m": TTL_CANDLE_5M,
    "15m": TTL_CANDLE_15M,
    "1H": TTL_CANDLE_1H,
    "1h": TTL_CANDLE_1H,
}


def _candle_ttl(timeframe: str) -> int:
    """Return TTL for *timeframe*, defaulting to 5 m when unknown."""
    return _CANDLE_TTL.get(timeframe, TTL_CANDLE_5M)


class MarketCache:
    """Serialize normalized market objects to Redis with type-specific TTLs.

    All public methods swallow :class:`RedisError` and log a warning so that
    cache outages never crash the collector pipeline.
    """

    def __init__(
        self,
        *,
        redis_url: str | None = None,
        client: redis.Redis | None = None,  # type: ignore[type-arg]
    ) -> None:
        """Create a market cache.

        Parameters
        ----------
        redis_url:
            Override Redis DSN (defaults to ``settings.redis_url``).
        client:
            Optional pre-built Redis client (used in tests with fakeredis).
        """
        self._redis_url = redis_url or settings.redis_url
        self._owns_client = client is None
        self._client: redis.Redis = client or redis.from_url(  # type: ignore[type-arg, assignment]
            self._redis_url,
            decode_responses=True,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_timeout,
        )

    def close(self) -> None:
        """Close the Redis connection if we own it."""
        if self._owns_client:
            try:
                self._client.close()
            except RedisError:
                log.warning("cache.close.failed")

    def _set(self, key: str, value: str, ttl: int) -> bool:
        """Write *value* to Redis with *ttl* seconds."""
        try:
            self._client.setex(key, ttl, value)
            log.debug("cache.set", key=key, ttl=ttl)
            return True
        except RedisError as exc:
            log.warning("cache.set.failed", key=key, error=type(exc).__name__)
            return False

    def _get(self, key: str) -> str | None:
        """Read a string value from Redis; ``None`` on miss or error."""
        try:
            value = self._client.get(key)
            if value is None:
                log.debug("cache.miss", key=key)
            return value
        except RedisError as exc:
            log.warning("cache.get.failed", key=key, error=type(exc).__name__)
            return None

    @staticmethod
    def _ticker_key(inst_id: str) -> str:
        return f"market:ticker:{inst_id}"

    @staticmethod
    def _candles_key(inst_id: str, timeframe: str) -> str:
        return f"market:candles:{inst_id}:{timeframe}"

    @staticmethod
    def _funding_key(inst_id: str) -> str:
        return f"market:funding:{inst_id}"

    @staticmethod
    def _instruments_key(inst_type: str) -> str:
        return f"market:instruments:{inst_type}"

    def set_ticker(self, ticker: NormalizedTicker) -> bool:
        """Cache a normalized ticker (TTL 30 s)."""
        payload = ticker.model_dump(mode="json")
        return self._set(self._ticker_key(ticker.inst_id), json.dumps(payload), TTL_TICKER)

    def get_ticker(self, inst_id: str) -> NormalizedTicker | None:
        """Return cached ticker or ``None`` on miss."""
        raw = self._get(self._ticker_key(inst_id))
        if raw is None:
            return None
        try:
            return NormalizedTicker.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("cache.ticker.deserialize_failed", inst_id=inst_id, error=str(exc))
            return None

    def set_candles(
        self,
        inst_id: str,
        timeframe: str,
        candles: list[NormalizedCandle],
    ) -> bool:
        """Cache a list of candles with timeframe-specific TTL."""
        payload = [c.model_dump(mode="json") for c in candles]
        ttl = _candle_ttl(timeframe)
        return self._set(
            self._candles_key(inst_id, timeframe),
            json.dumps(payload),
            ttl,
        )

    def get_candles(self, inst_id: str, timeframe: str) -> list[NormalizedCandle] | None:
        """Return cached candles or ``None`` on miss."""
        raw = self._get(self._candles_key(inst_id, timeframe))
        if raw is None:
            return None
        try:
            rows: list[dict[str, Any]] = json.loads(raw)
            return [NormalizedCandle.model_validate(r) for r in rows]
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning(
                "cache.candles.deserialize_failed",
                inst_id=inst_id,
                timeframe=timeframe,
                error=str(exc),
            )
            return None

    def set_funding_rate(self, rate: NormalizedFundingRate) -> bool:
        """Cache a funding-rate snapshot (TTL 8 h)."""
        payload = rate.model_dump(mode="json")
        return self._set(self._funding_key(rate.inst_id), json.dumps(payload), TTL_FUNDING_RATE)

    def get_funding_rate(self, inst_id: str) -> NormalizedFundingRate | None:
        """Return cached funding rate or ``None`` on miss."""
        raw = self._get(self._funding_key(inst_id))
        if raw is None:
            return None
        try:
            return NormalizedFundingRate.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("cache.funding.deserialize_failed", inst_id=inst_id, error=str(exc))
            return None

    def set_instruments(self, inst_type: str, instruments: list[dict[str, Any]]) -> bool:
        """Cache raw/normalized instrument dicts (TTL 24 h)."""
        return self._set(
            self._instruments_key(inst_type),
            json.dumps(instruments),
            TTL_INSTRUMENTS,
        )

    def get_instruments(self, inst_type: str) -> list[dict[str, Any]] | None:
        """Return cached instrument list or ``None`` on miss."""
        raw = self._get(self._instruments_key(inst_type))
        if raw is None:
            return None
        try:
            result: list[dict[str, Any]] = json.loads(raw)
            return result
        except json.JSONDecodeError as exc:
            log.warning("cache.instruments.deserialize_failed", inst_type=inst_type, error=str(exc))
            return None

    def get_ttl(self, key: str) -> int | None:
        """Return remaining TTL for *key* (test helper). ``None`` if key missing."""
        try:
            ttl = self._client.ttl(key)
            return ttl if ttl >= 0 else None
        except RedisError:
            return None
