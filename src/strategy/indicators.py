"""Shared technical indicators for strategy modules."""

from __future__ import annotations

from decimal import Decimal

from src.schemas.market import NormalizedCandle
from src.strategy.momentum import calc_ema

_ZERO = Decimal("0")


def _sort_candles(candles: list[NormalizedCandle]) -> list[NormalizedCandle]:
    return sorted(candles, key=lambda c: c.open_time)


def calc_atr(candles: list[NormalizedCandle], period: int = 14) -> float | None:
    """Calculate Average True Range as EMA of true range over *period* candles.

    True Range = max(high - low, abs(high - prev_close), abs(low - prev_close)).
    Returns absolute price units of the latest ATR, or ``None`` if insufficient data.
    """
    if period < 1:
        return None

    sorted_candles = _sort_candles(candles)
    if len(sorted_candles) < period + 1:
        return None

    true_ranges: list[Decimal] = []
    for i in range(1, len(sorted_candles)):
        current = sorted_candles[i]
        prev_close = sorted_candles[i - 1].close
        high_low = current.high - current.low
        high_prev = abs(current.high - prev_close)
        low_prev = abs(current.low - prev_close)
        true_ranges.append(max(high_low, high_prev, low_prev, _ZERO))

    if len(true_ranges) < period:
        return None

    atr = calc_ema(true_ranges, period)
    if atr is None:
        return None
    return float(atr)


def compute_atr_prices(
    entry_price: Decimal,
    direction: str,
    atr: float,
    sl_multiplier: float,
    tp_multiplier: float,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return (tp_price, sl_price, tp_pct, sl_pct) from ATR distances."""
    if atr <= 0:
        return entry_price, entry_price, _ZERO, _ZERO

    atr_d = Decimal(str(atr))
    sl_dist = atr_d * Decimal(str(sl_multiplier))
    tp_dist = atr_d * Decimal(str(tp_multiplier))
    side = direction.upper()

    if side == "LONG":
        tp_price = entry_price + tp_dist
        sl_price = entry_price - sl_dist
    else:
        tp_price = entry_price - tp_dist
        sl_price = entry_price + sl_dist

    if entry_price <= _ZERO:
        return tp_price, sl_price, _ZERO, _ZERO

    tp_pct = (abs(tp_price - entry_price) / entry_price * Decimal("100")).quantize(Decimal("0.0001"))
    sl_pct = (abs(sl_price - entry_price) / entry_price * Decimal("100")).quantize(Decimal("0.0001"))
    return tp_price, sl_price, tp_pct, sl_pct
