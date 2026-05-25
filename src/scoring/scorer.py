"""Multi-factor opportunity scorer with optional DB persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import Settings, get_settings
from src.db.models import Instrument, Opportunity, OpportunityScore, OpportunityStatus
from src.db.repositories.opportunity import OpportunityRepository
from src.schemas.scoring import Grade, ScoreBreakdown, ScoredOpportunity
from src.schemas.strategy import Candidate, StrategyType
from src.scoring.components import (
    compute_risk_penalty,
    score_funding,
    score_liquidity,
    score_momentum,
    score_spread,
    score_trend,
    score_volume,
)
from src.strategy.base import MarketContext
from src.utils.logger import get_logger

log = get_logger(__name__)

# Raw component ceilings from components.py (before strategy scaling).
_RAW_TREND_MAX = 25.0
_RAW_MOMENTUM_MAX = 20.0
_RAW_LIQUIDITY_MAX = 20.0
_RAW_VOLUME_MAX = 15.0
_RAW_FUNDING_MAX = 15.0
_RAW_SPREAD_MAX = 10.0


class _StrategyWeights:
    """Per-strategy component max scores (must sum to 100 before risk penalty)."""

    __slots__ = (
        "trend_max",
        "momentum_max",
        "liquidity_max",
        "volume_max",
        "funding_max",
        "spread_max",
    )

    def __init__(
        self,
        *,
        trend_max: float,
        momentum_max: float,
        liquidity_max: float,
        volume_max: float,
        funding_max: float,
        spread_max: float,
    ) -> None:
        self.trend_max = trend_max
        self.momentum_max = momentum_max
        self.liquidity_max = liquidity_max
        self.volume_max = volume_max
        self.funding_max = funding_max
        self.spread_max = spread_max


_FUNDING_WEIGHTS = _StrategyWeights(
    trend_max=0.0,
    momentum_max=0.0,
    liquidity_max=25.0,
    volume_max=15.0,
    funding_max=40.0,
    spread_max=20.0,
)

_MOMENTUM_WEIGHTS = _StrategyWeights(
    trend_max=30.0,
    momentum_max=25.0,
    liquidity_max=15.0,
    volume_max=20.0,
    funding_max=0.0,
    spread_max=10.0,
)

_CORRELATION_WEIGHTS = _StrategyWeights(
    trend_max=35.0,
    momentum_max=25.0,
    liquidity_max=15.0,
    volume_max=15.0,
    funding_max=0.0,
    spread_max=10.0,
)

_LIQUIDATION_WEIGHTS = _StrategyWeights(
    trend_max=15.0,
    momentum_max=20.0,
    liquidity_max=15.0,
    volume_max=15.0,
    funding_max=25.0,
    spread_max=10.0,
)

_STAT_ARB_WEIGHTS = _StrategyWeights(
    trend_max=10.0,
    momentum_max=10.0,
    liquidity_max=20.0,
    volume_max=10.0,
    funding_max=30.0,
    spread_max=20.0,
)


def _weights_for(strategy_type: StrategyType) -> _StrategyWeights:
    if strategy_type == StrategyType.FUNDING:
        return _FUNDING_WEIGHTS
    if strategy_type == StrategyType.MOMENTUM:
        return _MOMENTUM_WEIGHTS
    if strategy_type == StrategyType.CORRELATION_DIVERGENCE:
        return _CORRELATION_WEIGHTS
    if strategy_type == StrategyType.LIQUIDATION_ZONE:
        return _LIQUIDATION_WEIGHTS
    if strategy_type == StrategyType.STAT_ARBITRAGE:
        return _STAT_ARB_WEIGHTS
    if strategy_type in (
        StrategyType.BREAKOUT,
        StrategyType.VOLUME_ANOMALY,
        StrategyType.TREND_PULLBACK,
    ):
        return _MOMENTUM_WEIGHTS
    return _MOMENTUM_WEIGHTS


def _scale_component(raw: float, raw_max: float, target_max: float) -> float:
    """Linearly scale *raw* from ``[0, raw_max]`` to ``[0, target_max]``."""
    if target_max <= 0.0 or raw_max <= 0.0:
        return 0.0
    return round(min(raw / raw_max * target_max, target_max), 4)


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
    if "spread_pct" in signals:
        return float(signals["spread_pct"])
    ticker = context.ticker
    if ticker is None or ticker.bid_price is None or ticker.ask_price is None:
        return None
    bid, ask = ticker.bid_price, ticker.ask_price
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    mid = (bid + ask) / Decimal("2")
    return float((ask - bid) / mid * Decimal("100"))


def _volume_ratio(signals: dict) -> float | None:
    current = signals.get("current_volume")
    avg = signals.get("avg_volume_20")
    if current is None or avg is None:
        return None
    avg_f = float(avg)
    if avg_f <= 0:
        return None
    return float(current) / avg_f


def classify_grade(total: int, settings: Settings) -> Grade:
    """Map *total* score to a :class:`Grade` bucket."""
    if total >= settings.scoring_grade_excellent:
        return Grade.EXCELLENT
    if total >= settings.scoring_grade_good:
        return Grade.GOOD
    if total >= settings.scoring_grade_watch:
        return Grade.WATCH
    return Grade.IGNORE


class OpportunityScorer:
    """Compute 0–100 scores for strategy candidates."""

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
        self._model_version = self._settings.scoring_model_version

    def score(self, candidate: Candidate, context: MarketContext) -> ScoredOpportunity:
        """Score *candidate* using *context* market data.

        When a DB *session* was provided at construction, persists an
        :class:`~src.db.models.OpportunityScore` row and updates opportunity status.
        """
        signals = dict(candidate.raw_signals)
        ratio = _volume_ratio(signals)
        if ratio is not None:
            signals["volume_ratio"] = ratio

        spread_val = _spread_pct(context, signals)
        volume_val = _volume_24h_usd(context)
        funding_mag = (
            abs(float(context.funding_rate.funding_rate))
            if context.funding_rate is not None
            else None
        )

        weights = _weights_for(candidate.strategy_type)
        ticker = context.ticker

        raw_trend = score_trend(signals) if weights.trend_max > 0 else 0.0
        raw_momentum = score_momentum(signals) if weights.momentum_max > 0 else 0.0
        raw_liquidity = score_liquidity(ticker) if ticker and weights.liquidity_max > 0 else 0.0
        raw_volume = (
            score_volume(ticker, signals=signals)
            if ticker and weights.volume_max > 0
            else 0.0
        )
        raw_funding = (
            score_funding(context.funding_rate) if weights.funding_max > 0 else 0.0
        )
        raw_spread = (
            score_spread(ticker, max_spread_pct=self._settings.filter_max_spread_pct)
            if ticker and weights.spread_max > 0
            else 0.0
        )

        risk_penalty = compute_risk_penalty(
            spread_pct=spread_val,
            volume_24h_usd=volume_val,
            funding_magnitude=funding_mag,
            max_spread_pct=self._settings.risk_max_spread_pct,
            min_volume_usd=self._settings.risk_min_volume_usd,
            extreme_funding_rate=self._settings.risk_extreme_funding_rate,
        )
        if candidate.strategy_type == StrategyType.LIQUIDATION_ZONE:
            risk_penalty = min(risk_penalty + self._settings.liq_score_penalty, 30.0)

        breakdown = ScoreBreakdown(
            trend_score=_scale_component(raw_trend, _RAW_TREND_MAX, weights.trend_max),
            momentum_score=_scale_component(
                raw_momentum, _RAW_MOMENTUM_MAX, weights.momentum_max
            ),
            liquidity_score=_scale_component(
                raw_liquidity, _RAW_LIQUIDITY_MAX, weights.liquidity_max
            ),
            volume_score=_scale_component(raw_volume, _RAW_VOLUME_MAX, weights.volume_max),
            funding_score=_scale_component(
                raw_funding, _RAW_FUNDING_MAX, weights.funding_max
            ),
            spread_score=_scale_component(raw_spread, _RAW_SPREAD_MAX, weights.spread_max),
            risk_penalty=risk_penalty,
        )

        total = int(max(0, min(round(breakdown.raw_total), 100)))
        grade = classify_grade(total, self._settings)

        scored = ScoredOpportunity(
            candidate=candidate,
            breakdown=breakdown,
            total_score=total,
            grade=grade,
            model_version=self._model_version,
        )

        log.info(
            "scorer.result",
            symbol=candidate.symbol,
            strategy=candidate.strategy_type.value,
            total_score=total,
            grade=grade.value,
            trend=breakdown.trend_score,
            momentum=breakdown.momentum_score,
            liquidity=breakdown.liquidity_score,
            volume=breakdown.volume_score,
            funding=breakdown.funding_score,
            spread=breakdown.spread_score,
            risk_penalty=breakdown.risk_penalty,
        )

        if self._persist and self._session is not None:
            opp_id = self._persist_score(scored)
            scored = scored.model_copy(update={"opportunity_id": opp_id})

        return scored

    def _persist_score(self, scored: ScoredOpportunity) -> int | None:
        """Write score to DB; return opportunity id."""
        assert self._session is not None
        repo = OpportunityRepository(self._session)

        instrument = self._session.scalar(
            select(Instrument).where(Instrument.inst_id == scored.candidate.symbol),
        )
        if instrument is None:
            log.warning("scorer.persist.no_instrument", symbol=scored.candidate.symbol)
            return None

        opp = self._session.scalar(
            select(Opportunity)
            .where(
                Opportunity.instrument_id == instrument.id,
                Opportunity.strategy == scored.candidate.strategy_type.value,
                Opportunity.status == OpportunityStatus.DETECTED,
            )
            .order_by(Opportunity.detected_at.desc())
            .limit(1),
        )
        if opp is None:
            opp = repo.create_opportunity(scored.candidate)

        if opp is None:
            return None

        # Assign primary key before inserting the score row (same transaction).
        self._session.flush()
        opp_id = opp.id
        if opp_id is None:
            log.error(
                "scorer.persist.missing_opportunity_id",
                symbol=scored.candidate.symbol,
            )
            return None

        bd = scored.breakdown
        row = OpportunityScore(
            opportunity_id=opp_id,
            total_score=scored.total_score,
            trend_score=int(round(bd.trend_score)),
            momentum_score=int(round(bd.momentum_score)),
            volume_score=int(round(bd.volume_score)),
            volatility_score=int(round(bd.spread_score)),
            liquidity_score=int(round(bd.liquidity_score)),
            factors={
                "funding_score": bd.funding_score,
                "spread_score": bd.spread_score,
                "risk_penalty": bd.risk_penalty,
                "grade": scored.grade.value,
                "model_version": scored.model_version,
            },
            model_version=scored.model_version,
            scored_at=datetime.now(tz=timezone.utc),
            created_at=datetime.now(tz=timezone.utc),
        )
        self._session.add(row)
        opp.status = OpportunityStatus.SCORED
        opp.updated_at = datetime.now(tz=timezone.utc)
        self._session.flush()

        log.info(
            "scorer.persisted",
            opportunity_id=opp_id,
            symbol=scored.candidate.symbol,
            total_score=scored.total_score,
        )
        return opp_id
