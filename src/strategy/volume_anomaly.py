"""Volume spike / accumulation-distribution strategy."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from config.settings import Settings, get_settings
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.strategy.base import BaseStrategy, MarketContext
from src.strategy.momentum import _sort_candles
from src.utils.logger import get_logger

log = get_logger(__name__)

_HUNDRED = Decimal("100")
_ZERO = Decimal("0")


class VolumeAnomalyStrategy(BaseStrategy):
    """Detect volume spikes with muted price movement (accumulation/distribution)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return StrategyType.VOLUME_ANOMALY.value

    def scan(self, market_data: MarketContext) -> list[Candidate]:
        inst_id = market_data.inst_id
        try:
            if not market_data.candles_m15:
                return []

            candles = _sort_candles(market_data.candles_m15)
            if len(candles) < 21:
                return []

            spike = candles[-1]
            prior = candles[-21:-1]
            avg_vol = sum(c.volume for c in prior) / Decimal("20")
            if avg_vol <= _ZERO or spike.open <= _ZERO:
                return []

            volume_ratio = spike.volume / avg_vol
            if volume_ratio < Decimal(str(self._settings.volume_anomaly_multiplier)):
                return []

            price_change_pct = abs(spike.close - spike.open) / spike.open * _HUNDRED
            if price_change_pct >= Decimal(str(self._settings.volume_anomaly_max_price_change)):
                return []

            if spike.close > spike.open:
                direction = Direction.LONG
                spike_direction = "accumulation"
            elif spike.close < spike.open:
                direction = Direction.SHORT
                spike_direction = "distribution"
            else:
                return []

            confidence = min(float(volume_ratio / Decimal("8")), 1.0)
            candidate = Candidate(
                symbol=inst_id,
                strategy_type=StrategyType.VOLUME_ANOMALY,
                direction=direction,
                raw_signals={
                    "volume_ratio": str(volume_ratio.quantize(Decimal("0.0001"))),
                    "price_change_pct": str(price_change_pct.quantize(Decimal("0.0001"))),
                    "spike_candle_direction": spike_direction,
                    "current_volume": str(spike.volume),
                    "avg_volume_20": str(avg_vol.quantize(Decimal("0.0001"))),
                    "last_price": str(spike.close),
                },
                detected_at=datetime.now(tz=UTC),
                confidence=round(max(confidence, 0.5), 4),
            )
            log.info(
                "strategy.volume_anomaly.signal",
                inst_id=inst_id,
                direction=direction.value,
                volume_ratio=str(volume_ratio),
                price_change_pct=str(price_change_pct),
            )
            return [candidate]
        except Exception:
            log.exception("strategy.volume_anomaly.error", inst_id=inst_id)
            return []
