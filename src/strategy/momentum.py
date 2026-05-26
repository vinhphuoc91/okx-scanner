"""EMA / RSI momentum strategy."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from config.settings import Settings, get_settings
from src.schemas.market import NormalizedCandle
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.strategy.base import BaseStrategy, MarketContext
from src.utils.logger import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


def calc_ema(values: list[Decimal], period: int) -> Decimal | None:
    """Calculate Exponential Moving Average for the final value in *values*.

    Parameters
    ----------
    values:
        Price series ordered oldest → newest.
    period:
        EMA lookback window.

    Returns
    -------
    Decimal | None
        Latest EMA value, or ``None`` when insufficient data.
    """
    if period < 1 or len(values) < period:
        return None

    multiplier = Decimal("2") / (Decimal(period) + Decimal("1"))
    sma = sum(values[:period]) / Decimal(period)
    ema = sma
    for price in values[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def calc_rsi(values: list[Decimal], period: int = 14) -> Decimal | None:
    """Calculate Relative Strength Index for the final value in *values*.

    Uses Wilder's smoothing method.

    Parameters
    ----------
    values:
        Price series ordered oldest → newest.
    period:
        RSI lookback window (default 14).

    Returns
    -------
    Decimal | None
        Latest RSI (0–100), or ``None`` when insufficient data.
    """
    if period < 1 or len(values) < period + 1:
        return None

    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, _ZERO))
        losses.append(max(-delta, _ZERO))

    avg_gain = sum(gains[:period]) / Decimal(period)
    avg_loss = sum(losses[:period]) / Decimal(period)

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * Decimal(period - 1) + gains[i]) / Decimal(period)
        avg_loss = (avg_loss * Decimal(period - 1) + losses[i]) / Decimal(period)

    if avg_loss == _ZERO:
        return Decimal("100")
    rs = avg_gain / avg_loss
    return Decimal("100") - (Decimal("100") / (Decimal("1") + rs))


def _sort_candles(candles: list[NormalizedCandle]) -> list[NormalizedCandle]:
    """Return candles sorted oldest → newest."""
    return sorted(candles, key=lambda c: c.open_time)


def _closes(candles: list[NormalizedCandle]) -> list[Decimal]:
    return [c.close for c in candles]


class MomentumStrategy(BaseStrategy):
    """Detect trend + momentum + volume confluence opportunities.

    Rules (config-driven)
    ---------------------
    1. H1 EMA fast vs slow → trend direction
    2. M15 RSI → momentum alignment with trend
    3. M15 current volume > multiplier × 20-bar average → confirmation
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return StrategyType.MOMENTUM.value

    def scan(self, market_data: MarketContext) -> list[Candidate]:
        """Evaluate momentum conditions for one instrument."""
        inst_id = market_data.inst_id
        try:
            if not market_data.candles_m15 or not market_data.candles_h1:
                log.debug(
                    "strategy.momentum.skip",
                    inst_id=inst_id,
                    reason="missing_candles",
                )
                return []

            # Micro-cap filter: skip coins with 24h volume below threshold
            min_vol = Decimal(str(self._settings.momentum_min_volume_24h_usd))
            if min_vol > 0 and market_data.ticker is not None:
                ticker = market_data.ticker
                vol_24h = ticker.volume_24h_quote
                if vol_24h is None and ticker.volume_24h_base is not None and ticker.last_price > Decimal("0"):
                    vol_24h = ticker.volume_24h_base * ticker.last_price
                if vol_24h is None or vol_24h < min_vol:
                    log.debug(
                        "strategy.momentum.skip",
                        inst_id=inst_id,
                        reason="micro_cap_volume_below_min",
                        volume_24h_usd=str(vol_24h),
                        min_volume_usd=str(min_vol),
                    )
                    return []

            m15 = _sort_candles(market_data.candles_m15)
            h1 = _sort_candles(market_data.candles_h1)

            ema_fast_period = self._settings.momentum_ema_fast
            ema_slow_period = self._settings.momentum_ema_slow
            rsi_period = self._settings.momentum_rsi_period
            vol_lookback = 20

            h1_closes = _closes(h1)
            m15_closes = _closes(m15)

            ema_fast = calc_ema(h1_closes, ema_fast_period)
            ema_slow = calc_ema(h1_closes, ema_slow_period)
            rsi = calc_rsi(m15_closes, rsi_period)

            if ema_fast is None or ema_slow is None or rsi is None:
                log.debug(
                    "strategy.momentum.skip",
                    inst_id=inst_id,
                    reason="insufficient_indicator_data",
                )
                return []

            if len(m15) < vol_lookback + 1:
                log.debug(
                    "strategy.momentum.skip",
                    inst_id=inst_id,
                    reason="insufficient_volume_history",
                )
                return []

            current_vol = m15[-1].volume
            avg_vol = sum(c.volume for c in m15[-(vol_lookback + 1) : -1]) / Decimal(vol_lookback)
            vol_multiplier = Decimal(str(self._settings.momentum_volume_multiplier))
            volume_confirmed = current_vol > avg_vol * vol_multiplier

            rsi_bull = Decimal(str(self._settings.momentum_rsi_bull))
            rsi_bear = Decimal(str(self._settings.momentum_rsi_bear))

            uptrend = ema_fast > ema_slow
            downtrend = ema_fast < ema_slow
            rsi_bullish = rsi > rsi_bull
            rsi_bearish = rsi < rsi_bear

            direction: Direction | None = None
            if uptrend and rsi_bullish and volume_confirmed:
                direction = Direction.LONG
            elif downtrend and rsi_bearish and volume_confirmed:
                direction = Direction.SHORT

            signals = {
                "ema_fast": str(ema_fast),
                "ema_slow": str(ema_slow),
                "rsi": str(rsi),
                "current_volume": str(current_vol),
                "avg_volume_20": str(avg_vol),
                "volume_confirmed": volume_confirmed,
                "uptrend": uptrend,
                "downtrend": downtrend,
                "rsi_bullish": rsi_bullish,
                "rsi_bearish": rsi_bearish,
            }

            if direction is None:
                log.debug(
                    "strategy.momentum.no_signal",
                    inst_id=inst_id,
                    **{k: signals[k] for k in ("ema_fast", "ema_slow", "rsi", "volume_confirmed")},
                )
                return []

            confidence = self._calc_confidence(
                rsi=rsi,
                direction=direction,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                current_vol=current_vol,
                avg_vol=avg_vol,
            )

            candidate = Candidate(
                symbol=inst_id,
                strategy_type=StrategyType.MOMENTUM,
                direction=direction,
                raw_signals=signals,
                detected_at=datetime.now(tz=timezone.utc),
                confidence=confidence,
            )
            log.info(
                "strategy.momentum.signal",
                inst_id=inst_id,
                direction=direction.value,
                ema_fast=str(ema_fast),
                ema_slow=str(ema_slow),
                rsi=str(rsi),
                volume_confirmed=volume_confirmed,
                confidence=confidence,
            )
            return [candidate]

        except Exception:
            log.exception("strategy.momentum.error", inst_id=inst_id)
            return []

    def _calc_confidence(
        self,
        *,
        rsi: Decimal,
        direction: Direction,
        ema_fast: Decimal,
        ema_slow: Decimal,
        current_vol: Decimal,
        avg_vol: Decimal,
    ) -> float:
        """Heuristic confidence score from signal strength."""
        rsi_bull = Decimal(str(self._settings.momentum_rsi_bull))
        rsi_bear = Decimal(str(self._settings.momentum_rsi_bear))

        if direction == Direction.LONG:
            rsi_strength = min(float((rsi - rsi_bull) / Decimal("20")), 1.0)
        else:
            rsi_strength = min(float((rsi_bear - rsi) / Decimal("20")), 1.0)

        ema_gap = abs(ema_fast - ema_slow)
        ema_base = abs(ema_slow) if ema_slow != _ZERO else Decimal("1")
        trend_strength = min(float(ema_gap / ema_base * Decimal("100")), 1.0)

        vol_ratio = float(current_vol / avg_vol) if avg_vol > _ZERO else 1.0
        vol_strength = min(max(vol_ratio - 1.0, 0.0) / 2.0, 1.0)

        score = 0.4 * rsi_strength + 0.35 * trend_strength + 0.25 * vol_strength
        return round(max(0.5, min(score, 1.0)), 4)
