"""Unit tests for BreakoutStrategy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from config.settings import Settings
from src.schemas.market import NormalizedCandle
from src.schemas.strategy import Direction, StrategyType
from src.strategy.base import MarketContext
from src.strategy.breakout import BreakoutStrategy


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "breakout_consolidation_candles": 10,
        "breakout_range_max_pct": 2.0,
        "breakout_volume_multiplier": 2.0,
        "breakout_threshold_pct": 0.5,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _h1_candles(
    *,
    base: str = "100",
    last_close: str = "101",
    volume: str = "5000",
) -> list[NormalizedCandle]:
    candles: list[NormalizedCandle] = []
    price = Decimal(base)
    for i in range(25):
        t = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)
        close = price if i < 24 else Decimal(last_close)
        candles.append(
            NormalizedCandle(
                inst_id="BTC-USDT-SWAP",
                timeframe="1H",
                open_time=t,
                open=close - Decimal("0.2"),
                high=Decimal("100.5"),
                low=Decimal("99.5"),
                close=close,
                volume=Decimal("1000") if i < 24 else Decimal(volume),
            ),
        )
    return candles


@pytest.fixture
def strategy() -> BreakoutStrategy:
    return BreakoutStrategy(settings=_settings())


@pytest.mark.unit
class TestBreakoutStrategy:
    def test_long_breakout(self, strategy: BreakoutStrategy) -> None:
        ctx = MarketContext(
            symbol="BTC-USDT-SWAP",
            candles_h1=_h1_candles(last_close="101.2", volume="5000"),
        )
        results = strategy.scan(ctx)
        assert len(results) == 1
        assert results[0].direction == Direction.LONG
        assert results[0].strategy_type == StrategyType.BREAKOUT
        assert "resistance" in results[0].raw_signals

    def test_no_signal_wide_range(self, strategy: BreakoutStrategy) -> None:
        candles = _h1_candles(last_close="101.2", volume="5000")
        wide = [
            c.model_copy(update={"high": Decimal("110"), "low": Decimal("90")})
            if i >= 15
            else c
            for i, c in enumerate(candles)
        ]
        ctx = MarketContext(symbol="BTC-USDT-SWAP", candles_h1=wide)
        assert strategy.scan(ctx) == []
