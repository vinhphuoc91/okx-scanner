"""Statistical arbitrage — spot vs perpetual basis convergence."""

from __future__ import annotations

from datetime import datetime, timezone

from config.settings import Settings, get_settings
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.strategy.base import BaseStrategy, MarketContext
from src.strategy.helpers import basis_trend, calc_basis_pct
from src.utils.logger import get_logger

log = get_logger(__name__)


class StatArbitrageStrategy(BaseStrategy):
    """Trade perp premium/discount vs spot for mean-reversion."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return StrategyType.STAT_ARBITRAGE.value

    def scan(self, market_data: MarketContext) -> list[Candidate]:
        inst_id = market_data.inst_id
        try:
            perp = market_data.ticker
            spot = market_data.spot_ticker
            if perp is None or spot is None:
                log.debug("strategy.stat_arb.skip", inst_id=inst_id, reason="missing_spot_or_perp")
                return []

            basis = calc_basis_pct(spot.last_price, perp.last_price)
            if basis is None:
                log.debug("strategy.stat_arb.skip", inst_id=inst_id, reason="invalid_prices")
                return []

            min_basis = self._settings.stat_arb_min_basis
            strong_basis = self._settings.stat_arb_strong_basis

            direction: Direction | None = None
            if basis >= min_basis:
                direction = Direction.SHORT
            elif basis <= -min_basis:
                direction = Direction.LONG

            if direction is None:
                log.debug(
                    "strategy.stat_arb.no_signal",
                    inst_id=inst_id,
                    basis_pct=round(basis, 4),
                    min_basis=min_basis,
                )
                return []

            history = list(market_data.basis_history_pct)
            if basis not in history:
                history = history + [basis]
            trend = basis_trend(history[-self._settings.stat_arb_basis_trend_periods :])

            funding = market_data.funding_rate
            funding_rate = float(funding.funding_rate) if funding else 0.0
            convergence = False
            if trend is not None:
                if direction == Direction.SHORT and basis > 0 and trend < 0:
                    convergence = True
                if direction == Direction.LONG and basis < 0 and trend > 0:
                    convergence = True

            funding_aligned = (
                (direction == Direction.SHORT and funding_rate > 0)
                or (direction == Direction.LONG and funding_rate < 0)
            )

            abs_basis = abs(basis)
            confidence = 0.5
            if abs_basis >= strong_basis:
                confidence = 0.75
            elif abs_basis >= min_basis:
                confidence = 0.55 + (abs_basis - min_basis) / max(strong_basis - min_basis, 0.01) * 0.2
            if convergence:
                confidence = min(confidence + 0.1, 0.95)
            if funding_aligned:
                confidence = min(confidence + 0.05, 0.95)

            candidate = Candidate(
                symbol=inst_id,
                strategy_type=StrategyType.STAT_ARBITRAGE,
                direction=direction,
                raw_signals={
                    "spot_price": str(spot.last_price),
                    "perp_price": str(perp.last_price),
                    "basis_pct": str(round(basis, 4)),
                    "basis_trend": str(round(trend, 4)) if trend is not None else "",
                    "funding_rate": str(funding_rate),
                    "convergence_signal": str(convergence),
                    "spot_inst_id": spot.inst_id,
                    "last_price": str(perp.last_price),
                },
                detected_at=datetime.now(tz=timezone.utc),
                confidence=round(confidence, 4),
            )
            log.info(
                "strategy.stat_arb.signal",
                inst_id=inst_id,
                direction=direction.value,
                basis_pct=round(basis, 4),
                basis_trend=trend,
                convergence=convergence,
                funding_rate=funding_rate,
                confidence=confidence,
            )
            return [candidate]

        except Exception:
            log.exception("strategy.stat_arb.error", inst_id=inst_id)
            return []
