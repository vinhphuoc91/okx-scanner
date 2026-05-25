"""Hard-reject risk filter before alerting."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from config.settings import Settings, get_settings
from src.db.models import Opportunity, OpportunityStatus, RiskDecision as RiskDecisionRow
from src.db.models import RiskOutcome
from src.schemas.risk import RejectionCode, RiskDecision
from src.schemas.scoring import ScoredOpportunity
from src.strategy.base import MarketContext
from src.utils.logger import get_logger

log = get_logger(__name__)


def _volume_24h_usd(context: MarketContext) -> float | None:
    ticker = context.ticker
    if ticker is None:
        return None
    if ticker.volume_24h_quote is not None:
        return float(ticker.volume_24h_quote)
    if ticker.volume_24h_base is not None and ticker.last_price > 0:
        return float(ticker.volume_24h_base * ticker.last_price)
    return None


def _spread_pct(context: MarketContext, signals: dict) -> float | None:
    """Return spread from live ticker; fall back to strategy signals."""
    ticker = context.ticker
    if ticker is not None and ticker.bid_price is not None and ticker.ask_price is not None:
        bid, ask = ticker.bid_price, ticker.ask_price
        if bid > 0 and ask > 0 and ask >= bid:
            mid = (bid + ask) / Decimal("2")
            return float((ask - bid) / mid * Decimal("100"))
    if "spread_pct" in signals:
        return float(signals["spread_pct"])
    return None


class RiskFilter:
    """Apply hard reject rules to scored opportunities."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session: Session | None = None,
        persist: bool = True,
    ) -> None:
        self._settings = settings or get_settings()
        self._session = session
        self._persist = persist and session is not None

    def evaluate(
        self,
        scored: ScoredOpportunity,
        context: MarketContext,
        *,
        min_score: int | None = None,
    ) -> RiskDecision:
        """Evaluate hard rules; any failure rejects the opportunity."""
        signals = scored.candidate.raw_signals
        spread = _spread_pct(context, signals)
        volume = _volume_24h_usd(context)
        funding_mag = (
            abs(float(context.funding_rate.funding_rate))
            if context.funding_rate is not None
            else None
        )
        score_threshold = min_score if min_score is not None else self._settings.alert_min_score

        checks = {
            "spread_pct": spread,
            "max_spread_pct": self._settings.risk_max_spread_pct,
            "volume_24h_usd": volume,
            "min_volume_usd": self._settings.risk_min_volume_usd,
            "funding_magnitude": funding_mag,
            "extreme_funding_rate": self._settings.risk_extreme_funding_rate,
            "total_score": scored.total_score,
            "alert_min_score": score_threshold,
        }

        rejections: list[RejectionCode] = []

        if spread is not None and spread > self._settings.risk_max_spread_pct:
            rejections.append(RejectionCode.SPREAD_TOO_HIGH)
        if volume is not None and volume < self._settings.risk_min_volume_usd:
            rejections.append(RejectionCode.LOW_VOLUME)
        if (
            funding_mag is not None
            and funding_mag > self._settings.risk_extreme_funding_rate
        ):
            rejections.append(RejectionCode.EXTREME_FUNDING)
        if scored.total_score < score_threshold:
            rejections.append(RejectionCode.SCORE_TOO_LOW)

        approved = len(rejections) == 0
        decision = RiskDecision(
            approved=approved,
            rejection_codes=tuple(rejections),
            raw_checks=checks,
            opportunity_id=scored.opportunity_id,
        )

        if approved:
            log.info(
                "risk.approved",
                symbol=scored.candidate.symbol,
                total_score=scored.total_score,
                grade=scored.grade.value,
            )
        else:
            log.info(
                "risk.rejected",
                symbol=scored.candidate.symbol,
                total_score=scored.total_score,
                rejection_codes=[c.value for c in rejections],
                checks=checks,
            )

        if self._persist and self._session is not None and scored.opportunity_id:
            self._persist_decision(scored, decision)

        return decision

    def _persist_decision(
        self,
        scored: ScoredOpportunity,
        decision: RiskDecision,
    ) -> None:
        """Write risk decision to DB."""
        assert self._session is not None
        opp_id = scored.opportunity_id
        if opp_id is None:
            return

        outcome = RiskOutcome.APPROVED if decision.approved else RiskOutcome.REJECTED
        reason_code = (
            decision.rejection_codes[0].value
            if decision.rejection_codes
            else "APPROVED"
        )
        reason_detail = (
            ",".join(c.value for c in decision.rejection_codes)
            if decision.rejection_codes
            else None
        )

        row = RiskDecisionRow(
            opportunity_id=opp_id,
            outcome=outcome,
            reason_code=reason_code,
            reason_detail=reason_detail,
            snapshot=decision.raw_checks,
            decided_at=datetime.now(tz=timezone.utc),
            created_at=datetime.now(tz=timezone.utc),
        )
        self._session.add(row)

        opp = self._session.get(Opportunity, opp_id)
        if opp is not None:
            opp.status = (
                OpportunityStatus.APPROVED if decision.approved else OpportunityStatus.REJECTED
            )
            opp.updated_at = datetime.now(tz=timezone.utc)

        self._session.flush()
        log.info(
            "risk.persisted",
            opportunity_id=opp_id,
            outcome=outcome.value,
            reason_code=reason_code,
        )
