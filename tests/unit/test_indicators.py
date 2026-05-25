"""Unit tests for ATR indicator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.schemas.market import NormalizedCandle
from src.strategy.indicators import calc_atr, compute_atr_prices


def _candle(inst_id: str, i: int, *, high: str, low: str, close: str) -> NormalizedCandle:
    t = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)
    c = Decimal(close)
    return NormalizedCandle(
        inst_id=inst_id,
        timeframe="1H",
        open_time=t,
        open=c - Decimal("1"),
        high=Decimal(high),
        low=Decimal(low),
        close=c,
        volume=Decimal("1000"),
    )


class TestCalcAtr:
    def test_returns_positive_atr(self) -> None:
        candles = [
            _candle("BTC-USDT-SWAP", i, high="102", low="98", close="100")
            for i in range(20)
        ]
        atr = calc_atr(candles, period=14)
        assert atr is not None
        assert atr > 0

    def test_insufficient_data(self) -> None:
        candles = [_candle("BTC-USDT-SWAP", 0, high="101", low="99", close="100")]
        assert calc_atr(candles, period=14) is None


class TestComputeAtrPrices:
    def test_zero_atr_returns_entry(self) -> None:
        entry = Decimal("100")
        tp, sl, tp_pct, sl_pct = compute_atr_prices(entry, "LONG", 0.0, 1.5, 3.0)
        assert tp == entry
        assert sl == entry
        assert tp_pct == Decimal("0")
        assert sl_pct == Decimal("0")

    def test_long_atr_prices(self) -> None:
        entry = Decimal("100")
        tp, sl, tp_pct, sl_pct = compute_atr_prices(entry, "LONG", 2.0, 1.5, 3.0)
        assert tp == Decimal("106")
        assert sl == Decimal("97")
        assert tp_pct == Decimal("6.0000")
        assert sl_pct == Decimal("3.0000")

    def test_short_atr_prices(self) -> None:
        entry = Decimal("200")
        tp, sl, _, _ = compute_atr_prices(entry, "SHORT", 4.0, 2.0, 4.0)
        assert tp == Decimal("184")
        assert sl == Decimal("208")
