"""Funding-rate mean-reversion strategy."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from config.settings import Settings, get_settings
from src.schemas.market import NormalizedTicker
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.strategy.base import BaseStrategy, MarketContext
from src.utils.logger import get_logger

log = get_logger(__name__)

_HUNDRED = Decimal("100")
_ZERO = Decimal("0")


def _compute_spread_pct(ticker: NormalizedTicker) -> Decimal | None:
    """Return bid-ask spread as percentage of mid price."""
    bid, ask = ticker.bid_price, ticker.ask_price
    if bid is None or ask is None or bid <= _ZERO or ask <= _ZERO or ask < bid:
        return None
    mid = (bid + ask) / Decimal("2")
    if mid <= _ZERO:
        return None
    return (ask - bid) / mid * _HUNDRED


def _volume_24h_usd(ticker: NormalizedTicker) -> Decimal | None:
    """Estimate 24 h USD volume from ticker fields."""
    if ticker.volume_24h_quote is not None:
        return ticker.volume_24h_quote
    if ticker.volume_24h_base is not None and ticker.last_price > _ZERO:
        return ticker.volume_24h_base * ticker.last_price
    return None


def _funding_confidence(rate: Decimal, threshold: Decimal, direction: Direction) -> float:
    """Map funding-rate distance from threshold to confidence [0, 1]."""
    if threshold == _ZERO:
        return 0.5
    if direction == Direction.SHORT:
        excess = rate - threshold
        baseline = abs(threshold) if threshold != _ZERO else Decimal("0.0005")
    else:
        excess = threshold - rate
        baseline = abs(threshold) if threshold != _ZERO else Decimal("0.0002")
    if excess <= _ZERO:
        return 0.5
    ratio = min(float(excess / baseline), 3.0) / 3.0
    return round(0.5 + 0.5 * ratio, 4)


class FundingStrategy(BaseStrategy):
    """Detect opportunities from extreme perpetual funding rates.

    Rules (config-driven)
    ---------------------
    * Funding rate > ``funding_rate_short_threshold`` → SHORT
    * Funding rate < ``funding_rate_long_threshold`` → LONG
    * Spread ≤ ``filter_max_spread_pct``
    * Volume ≥ ``filter_min_volume_usd``
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return StrategyType.FUNDING.value

    def scan(self, market_data: MarketContext) -> list[Candidate]:
        """Evaluate funding-rate conditions for one instrument."""
        inst_id = market_data.inst_id
        try:
            if market_data.funding_rate is None:
                log.debug("strategy.funding.skip", inst_id=inst_id, reason="missing_funding_rate")
                return []
            if market_data.ticker is None:
                log.debug("strategy.funding.skip", inst_id=inst_id, reason="missing_ticker")
                return []

            ticker = market_data.ticker
            funding = market_data.funding_rate
            rate = funding.funding_rate

            spread = _compute_spread_pct(ticker)
            max_spread = Decimal(str(self._settings.filter_max_spread_pct))
            if spread is None:
                log.info(
                    "strategy.funding.rejected",
                    inst_id=inst_id,
                    reason="missing_spread",
                )
                return []
            if spread > max_spread:
                log.info(
                    "strategy.funding.rejected",
                    inst_id=inst_id,
                    reason="spread_above_max",
                    spread_pct=str(spread),
                    max_spread_pct=str(max_spread),
                )
                return []

            volume = _volume_24h_usd(ticker)
            min_volume = Decimal(str(self._settings.filter_min_volume_usd))
            if volume is None or volume < min_volume:
                log.info(
                    "strategy.funding.rejected",
                    inst_id=inst_id,
                    reason="volume_below_min",
                    volume_24h_usd=str(volume),
                    min_volume_usd=str(min_volume),
                )
                return []

            short_threshold = Decimal(str(self._settings.funding_rate_short_threshold))
            long_threshold = Decimal(str(self._settings.funding_rate_long_threshold))

            direction: Direction | None = None
            if rate > short_threshold:
                direction = Direction.SHORT
            elif rate < long_threshold:
                direction = Direction.LONG

            if direction is None:
                log.debug(
                    "strategy.funding.no_signal",
                    inst_id=inst_id,
                    funding_rate=str(rate),
                    short_threshold=str(short_threshold),
                    long_threshold=str(long_threshold),
                )
                return []

            threshold = short_threshold if direction == Direction.SHORT else long_threshold
            confidence = _funding_confidence(rate, threshold, direction)
            detected_at = datetime.now(tz=UTC)

            candidate = Candidate(
                symbol=inst_id,
                strategy_type=StrategyType.FUNDING,
                direction=direction,
                raw_signals={
                    "funding_rate": str(rate),
                    "funding_time": funding.funding_time.isoformat(),
                    "spread_pct": str(spread),
                    "volume_24h_usd": str(volume),
                    "short_threshold": str(short_threshold),
                    "long_threshold": str(long_threshold),
                    "last_price": str(ticker.last_price),
                },
                detected_at=detected_at,
                confidence=confidence,
            )
            log.info(
                "strategy.funding.signal",
                inst_id=inst_id,
                direction=direction.value,
                funding_rate=str(rate),
                spread_pct=str(spread),
                volume_24h_usd=str(volume),
                confidence=confidence,
            )
            return [candidate]

        except Exception:
            log.exception("strategy.funding.error", inst_id=inst_id)
            return []
