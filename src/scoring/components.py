"""Pure scoring component functions (0.0 → component max)."""

from __future__ import annotations

from decimal import Decimal

from src.schemas.market import NormalizedFundingRate, NormalizedTicker

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


def _to_float(value: Decimal | float | str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def score_trend(signals: dict) -> float:
    """Score trend strength from EMA signals (max 25).

    Expects ``ema_fast``, ``ema_slow``, and optional ``uptrend``/``downtrend`` booleans.
    Returns 0 when EMA data is absent.
    """
    ema_fast = signals.get("ema_fast")
    ema_slow = signals.get("ema_slow")
    if ema_fast is None or ema_slow is None:
        return 0.0

    fast = _to_float(ema_fast)
    slow = _to_float(ema_slow)
    if slow == 0.0:
        return 0.0

    gap_pct = abs(fast - slow) / abs(slow) * 100.0
    strength = min(gap_pct / 2.0, 1.0)  # 2% gap → full marks
    base = 12.5 + 12.5 * strength

    if signals.get("uptrend") is True or signals.get("downtrend") is True:
        return round(min(base, 25.0), 4)
    return round(min(base * 0.6, 25.0), 4)


def score_momentum(signals: dict) -> float:
    """Score RSI momentum alignment (max 20).

    Expects ``rsi`` plus optional ``rsi_bullish``/``rsi_bearish`` flags.
    """
    rsi_raw = signals.get("rsi")
    if rsi_raw is None:
        return 0.0

    rsi = _to_float(rsi_raw)
    if signals.get("rsi_bullish") is True:
        strength = min(max(rsi - 55.0, 0.0) / 25.0, 1.0)
    elif signals.get("rsi_bearish") is True:
        strength = min(max(45.0 - rsi, 0.0) / 25.0, 1.0)
    else:
        strength = min(abs(rsi - 50.0) / 30.0, 1.0)

    return round(20.0 * strength, 4)


def score_liquidity(ticker: NormalizedTicker) -> float:
    """Score 24 h USD liquidity (max 20)."""
    volume = ticker.volume_24h_quote
    if volume is None:
        if ticker.volume_24h_base is not None and ticker.last_price > _ZERO:
            volume = ticker.volume_24h_base * ticker.last_price
        else:
            return 0.0

    vol = _to_float(volume)
    if vol >= 50_000_000:
        return 20.0
    if vol >= 10_000_000:
        return 16.0
    if vol >= 5_000_000:
        return 12.0
    if vol >= 1_000_000:
        return 8.0
    if vol >= 500_000:
        return 4.0
    return 0.0


def score_volume(ticker: NormalizedTicker, *, signals: dict | None = None) -> float:
    """Score relative volume vs recent average (max 15).

    Uses ``volume_ratio`` from *signals* when present; otherwise derives a
    neutral score from ticker 24 h volume depth.
    """
    sig = signals or {}
    ratio_raw = sig.get("volume_ratio")
    if ratio_raw is not None:
        ratio = _to_float(ratio_raw)
        if ratio >= 2.0:
            return 15.0
        if ratio >= 1.5:
            return 12.0
        if ratio >= 1.2:
            return 8.0
        if ratio >= 1.0:
            return 5.0
        return 2.0

    # Fallback when only ticker is available (e.g. funding strategy)
    liq = score_liquidity(ticker)
    return round(min(liq / 20.0 * 10.0, 15.0), 4)


def score_funding(funding: NormalizedFundingRate | None) -> float:
    """Score funding-rate magnitude (max 15). Stronger extremes score higher."""
    if funding is None:
        return 0.0

    magnitude = abs(_to_float(funding.funding_rate))
    # 0.05% → ~5 pts, 0.10% → ~10 pts, 0.20%+ → 15 pts
    pts = min(magnitude / 0.002, 1.0) * 15.0
    return round(pts, 4)


def score_spread(ticker: NormalizedTicker, *, max_spread_pct: float = 0.5) -> float:
    """Score bid-ask tightness (max 10). Lower spread → higher score."""
    bid, ask = ticker.bid_price, ticker.ask_price
    if bid is None or ask is None or bid <= _ZERO or ask <= _ZERO or ask < bid:
        return 0.0

    mid = (bid + ask) / Decimal("2")
    spread_pct = float((ask - bid) / mid * _HUNDRED)
    if spread_pct <= 0.0:
        return 10.0
    if spread_pct >= max_spread_pct:
        return 0.0
    return round(10.0 * (1.0 - spread_pct / max_spread_pct), 4)


def compute_risk_penalty(
    *,
    spread_pct: float | None,
    volume_24h_usd: float | None,
    funding_magnitude: float | None,
    max_spread_pct: float,
    min_volume_usd: float,
    extreme_funding_rate: float,
) -> float:
    """Subtract up to 25 points for soft risk flags (max penalty -25)."""
    penalty = 0.0

    if spread_pct is not None and spread_pct > max_spread_pct * 0.8:
        penalty -= 8.0
    if volume_24h_usd is not None and volume_24h_usd < min_volume_usd * 1.5:
        penalty -= 8.0
    if funding_magnitude is not None and funding_magnitude > extreme_funding_rate * 0.8:
        penalty -= 9.0

    return max(penalty, -25.0)
