"""Unit tests for VolumeAnomalyStrategy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from config.settings import Settings
from src.schemas.market import NormalizedCandle
from src.schemas.strategy import Direction, StrategyType
from src.strategy.base import MarketContext
from src.strategy.volume_anomaly import VolumeAnomalyStrategy


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "volume_anomaly_multiplier": 4.0,
        "volume_anomaly_max_price_change": 1.5,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _m15_candles(*, spike_volume: str = "5000", close_gt_open: bool = True) -> list[NormalizedCandle]:
    candles: list[NormalizedCandle] = []
    for i in range(25):
        t = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * i)
        price = Decimal("100")
        if i == 24:
            o, c = (Decimal("100"), Decimal("100.3")) if close_gt_open else (Decimal("100.3"), Decimal("100"))
            vol = Decimal(spike_volume)
        else:
            o, c, vol = price, price, Decimal("1000")
        candles.append(
            NormalizedCandle(
                inst_id="ETH-USDT-SWAP",
                timeframe="15m",
                open_time=t,
                open=o,
                high=max(o, c) + Decimal("0.1"),
                low=min(o, c) - Decimal("0.1"),
                close=c,
                volume=vol,
            ),
        )
    return candles


@pytest.fixture
def strategy() -> VolumeAnomalyStrategy:
    return VolumeAnomalyStrategy(settings=_settings())


@pytest.mark.unit
class TestVolumeAnomalyStrategy:
    def test_long_accumulation(self, strategy: VolumeAnomalyStrategy) -> None:
        ctx = MarketContext(symbol="ETH-USDT-SWAP", candles_m15=_m15_candles())
        results = strategy.scan(ctx)
        assert len(results) == 1
        assert results[0].direction == Direction.LONG
        assert results[0].strategy_type == StrategyType.VOLUME_ANOMALY

    def test_short_distribution(self, strategy: VolumeAnomalyStrategy) -> None:
        ctx = MarketContext(
            symbol="ETH-USDT-SWAP",
            candles_m15=_m15_candles(close_gt_open=False),
        )
        results = strategy.scan(ctx)
        assert len(results) == 1
        assert results[0].direction == Direction.SHORT

    def test_reject_low_volume(self, strategy: VolumeAnomalyStrategy) -> None:
        ctx = MarketContext(
            symbol="ETH-USDT-SWAP",
            candles_m15=_m15_candles(spike_volume="1500"),
        )
        assert strategy.scan(ctx) == []
