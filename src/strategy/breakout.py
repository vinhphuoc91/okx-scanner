"""Consolidation breakout strategy."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from config.settings import Settings, get_settings
from src.schemas.market import NormalizedCandle
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.strategy.base import BaseStrategy, MarketContext
from src.strategy.momentum import _sort_candles
from src.utils.logger import get_logger

log = get_logger(__name__)

_HUNDRED = Decimal("100")
_ZERO = Decimal("0")


class BreakoutStrategy(BaseStrategy):
    """Detect range breakouts after H1 consolidation with volume confirmation."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return StrategyType.BREAKOUT.value

    def scan(self, market_data: MarketContext) -> list[Candidate]:
        inst_id = market_data.inst_id
        try:
            if not market_data.candles_h1:
                return []

            candles = _sort_candles(market_data.candles_h1)
            n = self._settings.breakout_consolidation_candles
            if len(candles) < max(n, 20):
                return []

            window = candles[-n:]
            resistance = max(c.high for c in window)
            support = min(c.low for c in window)
            mid = (resistance + support) / Decimal("2")
            if mid <= _ZERO:
                return []

            range_pct = (resistance - support) / mid * _HUNDRED
            if range_pct >= Decimal(str(self._settings.breakout_range_max_pct)):
                return []

            latest = candles[-1]
            threshold = Decimal(str(self._settings.breakout_threshold_pct)) / _HUNDRED
            direction: Direction | None = None
            breakout_pct = _ZERO

            if latest.close > resistance * (Decimal("1") + threshold):
                direction = Direction.LONG
                breakout_pct = (latest.close - resistance) / resistance * _HUNDRED
            elif latest.close < support * (Decimal("1") - threshold):
                direction = Direction.SHORT
                breakout_pct = (support - latest.close) / support * _HUNDRED

            if direction is None:
                return []

            vol_window = candles[-20:]
            avg_vol = sum(c.volume for c in vol_window) / Decimal(len(vol_window))
            if avg_vol <= _ZERO:
                return []
            volume_ratio = latest.volume / avg_vol
            if volume_ratio < Decimal(str(self._settings.breakout_volume_multiplier)):
                log.debug(
                    "strategy.breakout.rejected",
                    inst_id=inst_id,
                    reason="low_volume",
                    volume_ratio=str(volume_ratio),
                )
                return []

            confidence = min(float(volume_ratio / Decimal("4")), 1.0)
            candidate = Candidate(
                symbol=inst_id,
                strategy_type=StrategyType.BREAKOUT,
                direction=direction,
                raw_signals={
                    "resistance": str(resistance),
                    "support": str(support),
                    "range_pct": str(range_pct.quantize(Decimal("0.0001"))),
                    "volume_ratio": str(volume_ratio.quantize(Decimal("0.0001"))),
                    "breakout_pct": str(breakout_pct.quantize(Decimal("0.0001"))),
                    "current_volume": str(latest.volume),
                    "avg_volume_20": str(avg_vol.quantize(Decimal("0.0001"))),
                    "last_price": str(latest.close),
                },
                detected_at=datetime.now(tz=timezone.utc),
                confidence=round(max(confidence, 0.5), 4),
            )
            log.info(
                "strategy.breakout.signal",
                inst_id=inst_id,
                direction=direction.value,
                range_pct=str(range_pct),
                volume_ratio=str(volume_ratio),
            )
            return [candidate]
        except Exception:
            log.exception("strategy.breakout.error", inst_id=inst_id)
            return []
