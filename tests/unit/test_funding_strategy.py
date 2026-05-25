"""Unit tests for FundingStrategy."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from config.settings import Settings
from src.schemas.market import NormalizedFundingRate, NormalizedTicker
from src.schemas.strategy import Direction, StrategyType
from src.strategy.base import MarketContext
from src.strategy.funding import FundingStrategy


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "funding_rate_long_threshold": -0.0002,
        "funding_rate_short_threshold": 0.0005,
        "filter_min_volume_usd": 500_000.0,
        "filter_max_spread_pct": 0.5,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _ticker(
    inst_id: str = "BTC-USDT-SWAP",
    *,
    volume_quote: str = "5000000",
    bid: str = "100",
    ask: str = "100.1",
) -> NormalizedTicker:
    return NormalizedTicker(
        inst_id=inst_id,
        last_price=Decimal("100.05"),
        bid_price=Decimal(bid),
        ask_price=Decimal(ask),
        volume_24h_quote=Decimal(volume_quote),
    )


def _funding(rate: str, inst_id: str = "BTC-USDT-SWAP") -> NormalizedFundingRate:
    return NormalizedFundingRate(
        inst_id=inst_id,
        funding_rate=Decimal(rate),
        funding_time=datetime(2026, 5, 25, 8, 0, 0, tzinfo=UTC),
    )


def _ctx(
    rate: str,
    *,
    volume_quote: str = "5000000",
    bid: str = "100",
    ask: str = "100.1",
) -> MarketContext:
    return MarketContext(
        ticker=_ticker(volume_quote=volume_quote, bid=bid, ask=ask),
        funding_rate=_funding(rate),
    )


@pytest.fixture
def strategy() -> FundingStrategy:
    return FundingStrategy(settings=_settings())


@pytest.mark.unit
class TestFundingStrategySignals:
    def test_detect_short_when_funding_above_threshold(self, strategy: FundingStrategy) -> None:
        results = strategy.scan(_ctx("0.001"))
        assert len(results) == 1
        assert results[0].direction == Direction.SHORT
        assert results[0].strategy_type == StrategyType.FUNDING
        assert results[0].raw_signals["funding_rate"] == "0.001"

    def test_detect_long_when_funding_below_threshold(self, strategy: FundingStrategy) -> None:
        results = strategy.scan(_ctx("-0.0005"))
        assert len(results) == 1
        assert results[0].direction == Direction.LONG

    def test_no_signal_in_neutral_zone(self, strategy: FundingStrategy) -> None:
        results = strategy.scan(_ctx("0.0001"))
        assert results == []


@pytest.mark.unit
class TestFundingStrategyFilters:
    def test_rejects_high_spread(self, strategy: FundingStrategy) -> None:
        results = strategy.scan(_ctx("0.001", bid="100", ask="105"))
        assert results == []

    def test_rejects_low_volume(self, strategy: FundingStrategy) -> None:
        results = strategy.scan(_ctx("0.001", volume_quote="100000"))
        assert results == []

    def test_error_does_not_crash(self, strategy: FundingStrategy) -> None:
        ctx = MarketContext(ticker=None, funding_rate=_funding("0.001"))
        assert strategy.scan(ctx) == []
