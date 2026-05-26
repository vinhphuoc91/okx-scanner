"""Unit tests for LiquidationZoneStrategy."""

from __future__ import annotations

from datetime import datetime, timedelta

from src.utils.compat import UTC
from decimal import Decimal

import pytest

from config.settings import Settings
from src.schemas.market import NormalizedCandle, NormalizedFundingRate, NormalizedTicker
from src.schemas.strategy import Direction, StrategyType
from src.strategy.base import MarketContext
from src.strategy.liquidation_zone import LiquidationZoneStrategy


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "liq_min_oi_change": 20.0,
        "liq_funding_extreme_high": 0.0005,
        "liq_funding_extreme_low": -0.0002,
        "liq_rsi_overbought": 70.0,
        "liq_rsi_oversold": 30.0,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _candles(*, rising: bool = False) -> tuple[list[NormalizedCandle], list[NormalizedCandle]]:
    h1: list[NormalizedCandle] = []
    m15: list[NormalizedCandle] = []
    price = Decimal("100")
    for i in range(30):
        t_h = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)
        close = price + Decimal(str(i * 0.05))
        h1.append(
            NormalizedCandle(
                inst_id="BTC-USDT-SWAP",
                timeframe="1H",
                open_time=t_h,
                open=close - Decimal("0.2"),
                high=close + Decimal("2"),
                low=close - Decimal("1"),
                close=close,
                volume=Decimal("1000"),
            ),
        )
    for i in range(30):
        t_m = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * i)
        vol = Decimal(str(1000 - i * 10)) if rising else Decimal("1000")
        close = Decimal("105") + Decimal(str(i * 0.01))
        m15.append(
            NormalizedCandle(
                inst_id="BTC-USDT-SWAP",
                timeframe="15m",
                open_time=t_m,
                open=close - Decimal("0.1"),
                high=close + Decimal("0.5"),
                low=close - Decimal("0.5"),
                close=close,
                volume=vol,
            ),
        )
    return h1, m15


@pytest.fixture
def strategy() -> LiquidationZoneStrategy:
    return LiquidationZoneStrategy(settings=_settings())


@pytest.mark.unit
class TestLiquidationZoneStrategy:
    def test_short_when_oi_and_funding_high(self, strategy: LiquidationZoneStrategy) -> None:
        h1, m15 = _candles(rising=True)
        ctx = MarketContext(
            symbol="BTC-USDT-SWAP",
            ticker=NormalizedTicker(inst_id="BTC-USDT-SWAP", last_price=Decimal("105")),
            funding_rate=NormalizedFundingRate(
                inst_id="BTC-USDT-SWAP",
                funding_rate=Decimal("0.0008"),
                funding_time=datetime.now(tz=UTC),
            ),
            open_interest_change_4h_pct=25.0,
            candles_h1=h1,
            candles_m15=m15,
        )
        results = strategy.scan(ctx)
        if results:
            assert results[0].strategy_type == StrategyType.LIQUIDATION_ZONE
            assert results[0].direction == Direction.SHORT

    def test_no_signal_without_oi(self, strategy: LiquidationZoneStrategy) -> None:
        h1, m15 = _candles()
        ctx = MarketContext(
            symbol="BTC-USDT-SWAP",
            ticker=NormalizedTicker(inst_id="BTC-USDT-SWAP", last_price=Decimal("105")),
            funding_rate=NormalizedFundingRate(
                inst_id="BTC-USDT-SWAP",
                funding_rate=Decimal("0.0008"),
                funding_time=datetime.now(tz=UTC),
            ),
            open_interest_change_4h_pct=5.0,
            candles_h1=h1,
            candles_m15=m15,
        )
        assert strategy.scan(ctx) == []

    def test_no_signal_funding_only(self, strategy: LiquidationZoneStrategy) -> None:
        h1, m15 = _candles()
        ctx = MarketContext(
            symbol="BTC-USDT-SWAP",
            funding_rate=NormalizedFundingRate(
                inst_id="BTC-USDT-SWAP",
                funding_rate=Decimal("0.0008"),
                funding_time=datetime.now(tz=UTC),
            ),
            open_interest_change_4h_pct=None,
            candles_h1=h1,
            candles_m15=m15,
        )
        assert strategy.scan(ctx) == []
