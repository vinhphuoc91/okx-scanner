"""Unit tests for CorrelationDivergenceStrategy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from config.settings import Settings
from src.schemas.market import NormalizedCandle, NormalizedTicker
from src.schemas.strategy import Direction, StrategyType
from src.strategy.base import BenchmarkSnapshot, MarketContext
from src.strategy.correlation_divergence import CorrelationDivergenceStrategy


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "correlation_min_divergence": 1.5,
        "correlation_strong_divergence": 2.5,
        "correlation_min_tier": 2,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _h1_candles(*, start: str = "100", end: str = "103") -> list[NormalizedCandle]:
    candles: list[NormalizedCandle] = []
    start_p = Decimal(start)
    end_p = Decimal(end)
    for i in range(30):
        t = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)
        close = start_p if i < 29 else end_p
        candles.append(
            NormalizedCandle(
                inst_id="NEAR-USDT-SWAP",
                timeframe="1H",
                open_time=t,
                open=close - Decimal("0.1"),
                high=close + Decimal("0.5"),
                low=close - Decimal("0.5"),
                close=close,
                volume=Decimal("5000"),
            ),
        )
    return candles


def _benchmark(btc_change_1h: float = 3.0) -> BenchmarkSnapshot:
    return BenchmarkSnapshot(
        btc_change_1h=btc_change_1h,
        btc_change_4h=5.0,
        btc_change_24h=8.0,
        eth_change_1h=2.5,
        eth_change_4h=4.0,
        eth_change_24h=6.0,
        btc_trend_up=True,
        btc_price="70000",
        eth_price="3500",
    )


@pytest.fixture
def strategy() -> CorrelationDivergenceStrategy:
    return CorrelationDivergenceStrategy(settings=_settings())


@pytest.mark.unit
class TestCorrelationDivergenceStrategy:
    def test_long_when_btc_outperforms(self, strategy: CorrelationDivergenceStrategy) -> None:
        ctx = MarketContext(
            symbol="NEAR-USDT-SWAP",
            tier=1,
            ticker=NormalizedTicker(inst_id="NEAR-USDT-SWAP", last_price=Decimal("5")),
            candles_h1=_h1_candles(start="100", end="100.5"),
            candles_m15=_h1_candles(start="100", end="100.5"),
            benchmark=_benchmark(btc_change_1h=3.0),
        )
        results = strategy.scan(ctx)
        assert len(results) == 1
        assert results[0].direction == Direction.LONG
        assert results[0].strategy_type == StrategyType.CORRELATION_DIVERGENCE
        assert float(results[0].raw_signals["divergence_pct"]) >= 1.5

    def test_no_signal_when_btc_downtrend_for_long(self, strategy: CorrelationDivergenceStrategy) -> None:
        bench = BenchmarkSnapshot(
            btc_change_1h=3.0,
            btc_change_4h=1.0,
            btc_change_24h=-2.0,
            eth_change_1h=1.0,
            eth_change_4h=0.5,
            eth_change_24h=-1.0,
            btc_trend_up=False,
            btc_price="70000",
            eth_price="3500",
        )
        ctx = MarketContext(
            symbol="NEAR-USDT-SWAP",
            tier=1,
            candles_h1=_h1_candles(start="100", end="100.5"),
            candles_m15=_h1_candles(start="100", end="100.5"),
            benchmark=bench,
        )
        assert strategy.scan(ctx) == []

    def test_skip_tier3(self, strategy: CorrelationDivergenceStrategy) -> None:
        ctx = MarketContext(
            symbol="NEAR-USDT-SWAP",
            tier=3,
            candles_h1=_h1_candles(start="100", end="100.5"),
            benchmark=_benchmark(),
        )
        assert strategy.scan(ctx) == []

    def test_threshold_not_met(self, strategy: CorrelationDivergenceStrategy) -> None:
        ctx = MarketContext(
            symbol="NEAR-USDT-SWAP",
            tier=1,
            candles_h1=_h1_candles(start="100", end="102.5"),
            candles_m15=_h1_candles(start="100", end="102.5"),
            benchmark=_benchmark(btc_change_1h=3.0),
        )
        assert strategy.scan(ctx) == []
