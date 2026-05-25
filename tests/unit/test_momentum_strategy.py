"""Unit tests for MomentumStrategy and indicator helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from config.settings import Settings
from src.schemas.market import NormalizedCandle
from src.schemas.strategy import Direction, StrategyType
from src.strategy.base import MarketContext
from src.strategy.momentum import MomentumStrategy, calc_ema, calc_rsi


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "momentum_ema_fast": 20,
        "momentum_ema_slow": 50,
        "momentum_rsi_period": 14,
        "momentum_rsi_bull": 55.0,
        "momentum_rsi_bear": 45.0,
        "momentum_volume_multiplier": 1.5,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _candle(
    inst_id: str,
    timeframe: str,
    idx: int,
    *,
    close: str,
    volume: str = "1000",
) -> NormalizedCandle:
    t = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=idx)
    price = Decimal(close)
    return NormalizedCandle(
        inst_id=inst_id,
        timeframe=timeframe,
        open_time=t,
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price,
        volume=Decimal(volume),
    )


def _rising_closes(count: int, start: str = "100") -> list[Decimal]:
    base = Decimal(start)
    return [base + Decimal(i) for i in range(count)]


@pytest.mark.unit
class TestIndicators:
    def test_calc_ema_known_values(self) -> None:
        values = [Decimal(str(v)) for v in range(1, 31)]
        ema20 = calc_ema(values, 20)
        assert ema20 is not None
        assert ema20 > Decimal("20")

    def test_calc_ema_insufficient_data(self) -> None:
        assert calc_ema([Decimal("1"), Decimal("2")], 20) is None

    def test_calc_rsi_uptrend_high(self) -> None:
        values = _rising_closes(30, "100")
        rsi = calc_rsi(values, 14)
        assert rsi is not None
        assert rsi > Decimal("70")

    def test_calc_rsi_downtrend_low(self) -> None:
        values = [Decimal("100") - Decimal(i) for i in range(30)]
        rsi = calc_rsi(values, 14)
        assert rsi is not None
        assert rsi < Decimal("30")


@pytest.mark.unit
class TestMomentumStrategy:
    def _build_uptrend_context(self, *, volume: str = "5000") -> MarketContext:
        """H1 uptrend + M15 bullish RSI + volume spike on latest bar."""
        h1 = [
            _candle("BTC-USDT-SWAP", "1H", i, close=str(100 + i * 2))
            for i in range(60)
        ]
        m15 = [
            _candle("BTC-USDT-SWAP", "15m", i, close=str(100 + i), volume="1000")
            for i in range(25)
        ]
        m15[-1] = _candle("BTC-USDT-SWAP", "15m", 25, close="130", volume=volume)
        return MarketContext(symbol="BTC-USDT-SWAP", candles_m15=m15, candles_h1=h1)

    def test_detect_long_uptrend_momentum(self) -> None:
        strategy = MomentumStrategy(settings=_settings())
        results = strategy.scan(self._build_uptrend_context(volume="5000"))
        assert len(results) == 1
        assert results[0].direction == Direction.LONG
        assert results[0].strategy_type == StrategyType.MOMENTUM

    def test_detect_short_downtrend_momentum(self) -> None:
        h1 = [
            _candle("ETH-USDT-SWAP", "1H", i, close=str(200 - i * 2))
            for i in range(60)
        ]
        m15 = [
            _candle("ETH-USDT-SWAP", "15m", i, close=str(150 - i), volume="1000")
            for i in range(25)
        ]
        m15[-1] = _candle("ETH-USDT-SWAP", "15m", 25, close="120", volume="5000")
        strategy = MomentumStrategy(settings=_settings())
        results = strategy.scan(
            MarketContext(symbol="ETH-USDT-SWAP", candles_m15=m15, candles_h1=h1),
        )
        assert len(results) == 1
        assert results[0].direction == Direction.SHORT

    def test_no_signal_low_volume(self) -> None:
        strategy = MomentumStrategy(settings=_settings())
        results = strategy.scan(self._build_uptrend_context(volume="1100"))
        assert results == []

    def test_no_signal_mixed_trend_and_rsi(self) -> None:
        h1 = [
            _candle("BTC-USDT-SWAP", "1H", i, close=str(100 + i * 2))
            for i in range(60)
        ]
        m15 = [
            _candle("BTC-USDT-SWAP", "15m", i, close=str(150 - i), volume="1000")
            for i in range(25)
        ]
        m15[-1] = _candle("BTC-USDT-SWAP", "15m", 25, close="120", volume="5000")
        strategy = MomentumStrategy(settings=_settings())
        results = strategy.scan(
            MarketContext(symbol="BTC-USDT-SWAP", candles_m15=m15, candles_h1=h1),
        )
        assert results == []

    def test_error_does_not_crash(self) -> None:
        strategy = MomentumStrategy(settings=_settings())
        assert strategy.scan(MarketContext(symbol="X", candles_m15=[], candles_h1=[])) == []
