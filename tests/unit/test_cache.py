"""Unit tests for Redis market cache."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import fakeredis
import pytest

from src.collector.cache import (
    TTL_CANDLE_5M,
    TTL_CANDLE_15M,
    TTL_CANDLE_1H,
    TTL_FUNDING_RATE,
    TTL_TICKER,
    MarketCache,
)
from src.schemas.market import (
    NormalizedCandle,
    NormalizedFundingRate,
    NormalizedTicker,
)


@pytest.fixture
def cache() -> MarketCache:
    """In-memory Redis backed by fakeredis."""
    client = fakeredis.FakeRedis(decode_responses=True)
    return MarketCache(client=client)


def _sample_ticker(inst_id: str = "BTC-USDT") -> NormalizedTicker:
    return NormalizedTicker(
        inst_id=inst_id,
        last_price=Decimal("65000"),
        bid_price=Decimal("64999"),
        ask_price=Decimal("65001"),
        timestamp=datetime(2024, 5, 25, 12, 0, 0, tzinfo=UTC),
    )


def _sample_candle(inst_id: str = "BTC-USDT", timeframe: str = "5m") -> NormalizedCandle:
    return NormalizedCandle(
        inst_id=inst_id,
        timeframe=timeframe,
        open_time=datetime(2024, 5, 25, 12, 0, 0, tzinfo=UTC),
        open=Decimal("64000"),
        high=Decimal("65100"),
        low=Decimal("63900"),
        close=Decimal("65000"),
        volume=Decimal("123.45"),
    )


def _sample_funding(inst_id: str = "BTC-USDT-SWAP") -> NormalizedFundingRate:
    return NormalizedFundingRate(
        inst_id=inst_id,
        funding_rate=Decimal("0.0001"),
        funding_time=datetime(2024, 5, 25, 8, 0, 0, tzinfo=UTC),
    )


@pytest.mark.unit
class TestMarketCacheTicker:
    def test_set_and_get_ticker(self, cache: MarketCache) -> None:
        ticker = _sample_ticker()
        assert cache.set_ticker(ticker) is True
        loaded = cache.get_ticker("BTC-USDT")
        assert loaded is not None
        assert loaded.last_price == ticker.last_price

    def test_ticker_cache_miss(self, cache: MarketCache) -> None:
        assert cache.get_ticker("UNKNOWN") is None

    def test_ticker_ttl(self, cache: MarketCache) -> None:
        cache.set_ticker(_sample_ticker())
        ttl = cache.get_ttl(cache._ticker_key("BTC-USDT"))
        assert ttl is not None
        assert 0 < ttl <= TTL_TICKER


@pytest.mark.unit
class TestMarketCacheCandles:
    def test_set_and_get_candles(self, cache: MarketCache) -> None:
        candles = [_sample_candle()]
        assert cache.set_candles("BTC-USDT", "5m", candles) is True
        loaded = cache.get_candles("BTC-USDT", "5m")
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].close == Decimal("65000")

    def test_candles_cache_miss(self, cache: MarketCache) -> None:
        assert cache.get_candles("BTC-USDT", "5m") is None

    @pytest.mark.parametrize(
        ("timeframe", "expected_ttl"),
        [
            ("5m", TTL_CANDLE_5M),
            ("15m", TTL_CANDLE_15M),
            ("1H", TTL_CANDLE_1H),
        ],
    )
    def test_candle_ttl_by_timeframe(
        self,
        cache: MarketCache,
        timeframe: str,
        expected_ttl: int,
    ) -> None:
        cache.set_candles("ETH-USDT", timeframe, [_sample_candle("ETH-USDT", timeframe)])
        ttl = cache.get_ttl(cache._candles_key("ETH-USDT", timeframe))
        assert ttl is not None
        assert 0 < ttl <= expected_ttl


@pytest.mark.unit
class TestMarketCacheFunding:
    def test_set_and_get_funding_rate(self, cache: MarketCache) -> None:
        rate = _sample_funding()
        assert cache.set_funding_rate(rate) is True
        loaded = cache.get_funding_rate("BTC-USDT-SWAP")
        assert loaded is not None
        assert loaded.funding_rate == Decimal("0.0001")

    def test_funding_cache_miss(self, cache: MarketCache) -> None:
        assert cache.get_funding_rate("UNKNOWN-SWAP") is None

    def test_funding_ttl(self, cache: MarketCache) -> None:
        cache.set_funding_rate(_sample_funding())
        ttl = cache.get_ttl(cache._funding_key("BTC-USDT-SWAP"))
        assert ttl is not None
        assert 0 < ttl <= TTL_FUNDING_RATE
