"""Unit tests for TrendPullbackStrategy."""

from __future__ import annotations

from datetime import datetime, timedelta

from src.utils.compat import UTC
from decimal import Decimal

import pytest

from config.settings import Settings
from src.schemas.market import NormalizedCandle
from src.schemas.strategy import Direction, StrategyType
from src.strategy.base import MarketContext
from src.strategy.momentum import _closes, calc_ema
from src.strategy.trend_pullback import TrendPullbackStrategy


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "trend_pullback_ema_fast": 20,
        "trend_pullback_ema_slow": 50,
        "trend_pullback_tolerance_pct": 0.5,
        "trend_pullback_min_angle": 0.01,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _rising_candles(
    inst_id: str,
    timeframe: str,
    count: int,
    *,
    start: str = "100",
    step: str = "0.5",
    delta_minutes: int = 60,
) -> list[NormalizedCandle]:
    candles: list[NormalizedCandle] = []
    base = Decimal(start)
    step_d = Decimal(step)
    for i in range(count):
        t = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=delta_minutes * i)
        close = base + step_d * Decimal(i)
        candles.append(
            NormalizedCandle(
                inst_id=inst_id,
                timeframe=timeframe,
                open_time=t,
                open=close - Decimal("0.1"),
                high=close + Decimal("0.5"),
                low=close - Decimal("0.5"),
                close=close,
                volume=Decimal("2000"),
            ),
        )
    return candles


@pytest.fixture
def strategy() -> TrendPullbackStrategy:
    return TrendPullbackStrategy(settings=_settings())


@pytest.mark.unit
class TestTrendPullbackStrategy:
    def test_uptrend_pullback_long(self, strategy: TrendPullbackStrategy) -> None:
        h1 = _rising_candles("SOL-USDT-SWAP", "1H", 60, step="1")
        m15 = _rising_candles("SOL-USDT-SWAP", "15m", 60, step="0.2", delta_minutes=15)
        ema20 = calc_ema(_closes(m15), 20)
        assert ema20 is not None
        m15[-1] = m15[-1].model_copy(
            update={
                "open": ema20 - Decimal("0.05"),
                "close": ema20,
                "high": ema20 + Decimal("0.1"),
                "low": ema20 - Decimal("0.1"),
                "volume": Decimal("5000"),
            },
        )
        ctx = MarketContext(symbol="SOL-USDT-SWAP", candles_h1=h1, candles_m15=m15)
        results = strategy.scan(ctx)
        assert len(results) == 1
        assert results[0].direction == Direction.LONG
        assert results[0].strategy_type == StrategyType.TREND_PULLBACK

    def test_insufficient_data(self, strategy: TrendPullbackStrategy) -> None:
        ctx = MarketContext(symbol="SOL-USDT-SWAP", candles_h1=[], candles_m15=[])
        assert strategy.scan(ctx) == []
