"""Shared helpers for advanced strategy modules."""

from __future__ import annotations

from decimal import Decimal

from src.schemas.market import NormalizedCandle
from src.strategy.momentum import _closes, calc_ema, calc_rsi

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


def swap_to_spot_id(inst_id: str) -> str | None:
    """Map ``BTC-USDT-SWAP`` → ``BTC-USDT``."""
    if not inst_id.endswith("-SWAP"):
        return None
    return inst_id.removesuffix("-SWAP")


def sort_candles(candles: list[NormalizedCandle]) -> list[NormalizedCandle]:
    return sorted(candles, key=lambda c: c.open_time)


def calc_price_change_pct(candles: list[NormalizedCandle], periods: int) -> float | None:
    """Return percent change from *periods* bars ago to latest close."""
    sorted_c = sort_candles(candles)
    if len(sorted_c) <= periods:
        return None
    latest = sorted_c[-1].close
    prior = sorted_c[-1 - periods].close
    if prior <= _ZERO:
        return None
    return float((latest - prior) / prior * _HUNDRED)


def btc_uptrend_h1(candles_h1: list[NormalizedCandle]) -> bool | None:
    """True when EMA20 > EMA50 on H1 closes."""
    closes = _closes(sort_candles(candles_h1))
    if len(closes) < 50:
        return None
    ema_fast = calc_ema(closes, 20)
    ema_slow = calc_ema(closes, 50)
    if ema_fast is None or ema_slow is None:
        return None
    return ema_fast > ema_slow


def volume_not_declining(candles_m15: list[NormalizedCandle], *, lookback: int = 20) -> bool:
    """Volume of latest bar >= average of prior bars (coin not dying)."""
    sorted_c = sort_candles(candles_m15)
    if len(sorted_c) < lookback + 1:
        return True
    recent = sorted_c[-lookback - 1 : -1]
    avg_vol = sum(c.volume for c in recent) / Decimal(str(len(recent)))
    if avg_vol <= _ZERO:
        return True
    return sorted_c[-1].volume >= avg_vol * Decimal("0.8")


def calc_bollinger(
    candles: list[NormalizedCandle],
    *,
    period: int = 20,
    std_mult: float = 2.0,
) -> tuple[Decimal, Decimal, Decimal] | None:
    """Return (lower, middle, upper) Bollinger bands on closes."""
    closes = _closes(sort_candles(candles))
    if len(closes) < period:
        return None
    window = closes[-period:]
    middle = sum(window) / Decimal(str(period))
    variance = sum((c - middle) ** 2 for c in window) / Decimal(str(period))
    if variance <= _ZERO:
        std = _ZERO
    else:
        std = variance.sqrt()
    band = std * Decimal(str(std_mult))
    return middle - band, middle, middle + band


def bb_position(price: Decimal, lower: Decimal, upper: Decimal) -> float | None:
    """Return 0–1 position within Bollinger band (0=lower, 1=upper)."""
    width = upper - lower
    if width <= _ZERO:
        return None
    pos = (price - lower) / width
    return float(max(Decimal("0"), min(pos, Decimal("1"))))


def volume_trend_declining(candles_m15: list[NormalizedCandle], *, periods: int = 5) -> bool:
    """True when recent volume is declining (exhaustion)."""
    sorted_c = sort_candles(candles_m15)
    if len(sorted_c) < periods + 1:
        return False
    vols = [float(c.volume) for c in sorted_c[-periods - 1 :]]
    return all(vols[i] >= vols[i + 1] for i in range(len(vols) - 1))


def calc_rsi_value(candles: list[NormalizedCandle], period: int = 14) -> float | None:
    closes = _closes(sort_candles(candles))
    rsi = calc_rsi(closes, period)
    return float(rsi) if rsi is not None else None


def calc_basis_pct(spot_price: Decimal, perp_price: Decimal) -> float | None:
    if spot_price <= _ZERO:
        return None
    return float((perp_price - spot_price) / spot_price * _HUNDRED)


def basis_trend(values: list[float]) -> float | None:
    """Return change from oldest to newest basis (negative = converging toward zero)."""
    if len(values) < 2:
        return None
    return values[-1] - values[0]
