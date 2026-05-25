"""Trend pullback bounce strategy."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from config.settings import Settings, get_settings
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.strategy.base import BaseStrategy, MarketContext
from src.strategy.momentum import _closes, _sort_candles, calc_ema
from src.utils.logger import get_logger

log = get_logger(__name__)

_HUNDRED = Decimal("100")
_ZERO = Decimal("0")


class TrendPullbackStrategy(BaseStrategy):
    """Detect pullbacks to EMA20 within an established H1 trend."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return StrategyType.TREND_PULLBACK.value

    def scan(self, market_data: MarketContext) -> list[Candidate]:
        inst_id = market_data.inst_id
        try:
            if not market_data.candles_h1 or not market_data.candles_m15:
                return []

            h1 = _sort_candles(market_data.candles_h1)
            m15 = _sort_candles(market_data.candles_m15)
            fast = self._settings.trend_pullback_ema_fast
            slow = self._settings.trend_pullback_ema_slow

            if len(h1) < slow + 2 or len(m15) < fast + 21:
                return []

            h1_closes = _closes(h1)
            ema20_h1 = calc_ema(h1_closes, fast)
            ema50_h1 = calc_ema(h1_closes, slow)
            if ema20_h1 is None or ema50_h1 is None:
                return []

            ema20_prev = calc_ema(h1_closes[:-1], fast)
            if ema20_prev is None or ema20_prev <= _ZERO:
                return []
            trend_angle = (ema20_h1 - ema20_prev) / ema20_prev * _HUNDRED
            min_angle = Decimal(str(self._settings.trend_pullback_min_angle))

            uptrend = ema20_h1 > ema50_h1 and trend_angle >= min_angle
            downtrend = ema20_h1 < ema50_h1 and trend_angle <= -min_angle
            if not uptrend and not downtrend:
                return []

            m15_closes = _closes(m15)
            ema20_m15 = calc_ema(m15_closes, fast)
            if ema20_m15 is None or ema20_m15 <= _ZERO:
                return []

            latest = m15[-1]
            tolerance = Decimal(str(self._settings.trend_pullback_tolerance_pct)) / _HUNDRED
            dist_pct = abs(latest.close - ema20_m15) / ema20_m15

            if dist_pct > tolerance:
                return []

            vol_window = m15[-21:-1]
            avg_vol = sum(c.volume for c in vol_window) / Decimal("20")
            bounce_vol_ok = avg_vol > _ZERO and latest.volume >= avg_vol * Decimal("1.2")

            direction: Direction | None = None
            bounce_confirmed = False

            if uptrend and latest.close > latest.open:
                direction = Direction.LONG
                bounce_confirmed = bounce_vol_ok
            elif downtrend and latest.close < latest.open:
                direction = Direction.SHORT
                bounce_confirmed = bounce_vol_ok

            if direction is None or not bounce_confirmed:
                return []

            pullback_pct = dist_pct * _HUNDRED
            ratio = min_angle / max(abs(trend_angle), min_angle)
            confidence = min(float(ratio * Decimal("0.5") + Decimal("0.5")), 1.0)

            candidate = Candidate(
                symbol=inst_id,
                strategy_type=StrategyType.TREND_PULLBACK,
                direction=direction,
                raw_signals={
                    "ema20": str(ema20_m15.quantize(Decimal("0.0001"))),
                    "ema50": str(ema50_h1.quantize(Decimal("0.0001"))),
                    "trend_angle": str(trend_angle.quantize(Decimal("0.0001"))),
                    "pullback_pct": str(pullback_pct.quantize(Decimal("0.0001"))),
                    "bounce_confirmed": bounce_confirmed,
                    "current_volume": str(latest.volume),
                    "avg_volume_20": str(avg_vol.quantize(Decimal("0.0001"))),
                    "last_price": str(latest.close),
                },
                detected_at=datetime.now(tz=UTC),
                confidence=round(confidence, 4),
            )
            log.info(
                "strategy.trend_pullback.signal",
                inst_id=inst_id,
                direction=direction.value,
                pullback_pct=str(pullback_pct),
                trend_angle=str(trend_angle),
            )
            return [candidate]
        except Exception:
            log.exception("strategy.trend_pullback.error", inst_id=inst_id)
            return []
