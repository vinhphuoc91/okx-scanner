"""Liquidation zone — over-leveraged markets with exhaustion confirmation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from config.settings import Settings, get_settings
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.strategy.base import BaseStrategy, MarketContext
from src.strategy.helpers import (
    bb_position,
    calc_bollinger,
    calc_rsi_value,
    volume_trend_declining,
)
from src.utils.logger import get_logger

log = get_logger(__name__)


class LiquidationZoneStrategy(BaseStrategy):
    """Fade over-extended leverage when funding + OI spike with exhaustion."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return StrategyType.LIQUIDATION_ZONE.value

    def scan(self, market_data: MarketContext) -> list[Candidate]:
        inst_id = market_data.inst_id
        try:
            funding = market_data.funding_rate
            if funding is None:
                log.debug("strategy.liquidation.skip", inst_id=inst_id, reason="missing_funding")
                return []

            oi_change = market_data.open_interest_change_4h_pct
            if oi_change is None:
                log.debug("strategy.liquidation.skip", inst_id=inst_id, reason="missing_oi")
                return []

            min_oi = self._settings.liq_min_oi_change
            if oi_change < min_oi:
                log.debug(
                    "strategy.liquidation.no_signal",
                    inst_id=inst_id,
                    oi_change_4h=oi_change,
                    min_required=min_oi,
                )
                return []

            rate = float(funding.funding_rate)
            high_thr = self._settings.liq_funding_extreme_high
            low_thr = self._settings.liq_funding_extreme_low
            funding_extreme = rate >= high_thr or rate <= low_thr
            if not funding_extreme:
                log.debug(
                    "strategy.liquidation.no_signal",
                    inst_id=inst_id,
                    funding_rate=rate,
                    reason="funding_not_extreme",
                )
                return []

            rsi = calc_rsi_value(market_data.candles_m15)
            if rsi is None:
                log.debug("strategy.liquidation.skip", inst_id=inst_id, reason="missing_rsi")
                return []

            bb = calc_bollinger(market_data.candles_h1)
            ticker = market_data.ticker
            if bb is None or ticker is None:
                log.debug("strategy.liquidation.skip", inst_id=inst_id, reason="missing_bb_or_ticker")
                return []

            lower, _mid, upper = bb
            bb_pos = bb_position(ticker.last_price, lower, upper)
            vol_declining = volume_trend_declining(market_data.candles_m15)

            direction: Direction | None = None
            ob = self._settings.liq_rsi_overbought
            os_level = self._settings.liq_rsi_oversold

            if rate >= high_thr and rsi >= ob:
                direction = Direction.SHORT
            elif rate <= low_thr and rsi <= os_level:
                direction = Direction.LONG

            if direction is None:
                log.debug(
                    "strategy.liquidation.no_signal",
                    inst_id=inst_id,
                    rsi=rsi,
                    funding_rate=rate,
                    reason="rsi_not_confirmed",
                )
                return []

            near_band = bb_pos is not None and (bb_pos >= 0.85 or bb_pos <= 0.15)
            if not near_band:
                log.debug("strategy.liquidation.skip", inst_id=inst_id, reason="not_near_bb_extreme")
                return []

            if not vol_declining:
                log.debug("strategy.liquidation.skip", inst_id=inst_id, reason="volume_not_declining")
                return []

            leverage_est = oi_change * abs(rate) * 1000
            confidence = min(0.5 + oi_change / 100 * 0.3 + abs(rate) / high_thr * 0.2, 0.95)

            candidate = Candidate(
                symbol=inst_id,
                strategy_type=StrategyType.LIQUIDATION_ZONE,
                direction=direction,
                raw_signals={
                    "oi_change_4h": str(round(oi_change, 4)),
                    "funding_rate": str(funding.funding_rate),
                    "rsi": str(round(rsi, 2)),
                    "bb_position": str(round(bb_pos, 4)) if bb_pos is not None else "",
                    "volume_trend": "declining" if vol_declining else "flat",
                    "leverage_estimate": str(round(leverage_est, 4)),
                    "last_price": str(ticker.last_price),
                },
                detected_at=datetime.now(tz=UTC),
                confidence=round(confidence, 4),
            )
            log.info(
                "strategy.liquidation.signal",
                inst_id=inst_id,
                direction=direction.value,
                oi_change_4h=round(oi_change, 4),
                funding_rate=rate,
                rsi=round(rsi, 2),
                bb_position=bb_pos,
                confidence=confidence,
            )
            return [candidate]

        except Exception:
            log.exception("strategy.liquidation.error", inst_id=inst_id)
            return []
