"""Opportunity repository — persist and query strategy candidates."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from src.db.models import (
    Alert,
    Instrument,
    Opportunity,
    OpportunityScore,
    OpportunitySide,
    OpportunityStatus,
    RiskDecision,
    RiskOutcome,
)
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.utils.logger import get_logger

log = get_logger(__name__)

_PENDING_STATUSES = (OpportunityStatus.DETECTED, OpportunityStatus.SCORED)


class OpportunityRepository:
    """CRUD helpers for :class:`~src.db.models.Opportunity`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_opportunity(self, candidate: Candidate) -> Opportunity | None:
        """Persist a :class:`Candidate` as a new opportunity row.

        Returns ``None`` when the instrument is not found in the DB.
        """
        instrument = self._session.scalar(
            select(Instrument).where(Instrument.inst_id == candidate.symbol),
        )
        if instrument is None:
            log.warning(
                "opportunity.create.not_found",
                symbol=candidate.symbol,
                strategy=candidate.strategy_type.value,
            )
            return None

        entry_price = Decimal(
            candidate.raw_signals.get("last_price", "0"),
        )
        if entry_price <= 0 and candidate.raw_signals.get("ema_fast"):
            entry_price = Decimal(candidate.raw_signals["ema_fast"])

        side = (
            OpportunitySide.LONG
            if candidate.direction == Direction.LONG
            else OpportunitySide.SHORT
        )

        now = datetime.now(tz=timezone.utc)
        row = Opportunity(
            instrument_id=instrument.id,
            strategy=candidate.strategy_type.value,
            side=side,
            status=OpportunityStatus.DETECTED,
            entry_price=entry_price if entry_price > 0 else Decimal("1"),
            detected_at=candidate.detected_at,
            context={
                **candidate.raw_signals,
                "confidence": candidate.confidence,
                "direction": candidate.direction.value,
            },
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        log.info(
            "opportunity.created",
            symbol=candidate.symbol,
            strategy=candidate.strategy_type.value,
            side=side.value,
            confidence=candidate.confidence,
        )
        return row

    def get_pending_opportunities(self) -> list[Opportunity]:
        """Return opportunities awaiting scoring / risk review."""
        stmt = (
            select(Opportunity)
            .where(Opportunity.status.in_(_PENDING_STATUSES))
            .order_by(Opportunity.detected_at.desc())
        )
        return list(self._session.scalars(stmt).all())

    def update_opportunity_status(
        self,
        opportunity_id: int,
        status: OpportunityStatus | str,
    ) -> Opportunity | None:
        """Update lifecycle status for one opportunity."""
        row = self._session.get(Opportunity, opportunity_id)
        if row is None:
            log.warning("opportunity.status.not_found", opportunity_id=opportunity_id)
            return None

        resolved = (
            status if isinstance(status, OpportunityStatus) else OpportunityStatus(status)
        )
        row.status = resolved
        row.updated_at = datetime.now(tz=timezone.utc)
        log.info(
            "opportunity.status.updated",
            opportunity_id=opportunity_id,
            status=resolved.value,
        )
        return row

    def get_opportunities(
        self,
        *,
        grade: str | None = None,
        strategy: str | None = None,
        direction: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return approved opportunities with their latest score.

        Deduplicated to one row per ``(instrument_id, strategy, direction)``.
        """
        latest_opp_sq = (
            select(
                Opportunity.instrument_id,
                Opportunity.strategy,
                Opportunity.side,
                func.max(Opportunity.id).label("latest_id"),
            )
            .where(Opportunity.status == OpportunityStatus.APPROVED)
            .group_by(
                Opportunity.instrument_id,
                Opportunity.strategy,
                Opportunity.side,
            )
            .subquery()
        )

        latest_score_sq = (
            select(
                OpportunityScore.opportunity_id,
                func.max(OpportunityScore.scored_at).label("max_scored_at"),
            )
            .group_by(OpportunityScore.opportunity_id)
            .subquery()
        )

        stmt = (
            select(Opportunity, OpportunityScore, Instrument)
            .join(latest_opp_sq, Opportunity.id == latest_opp_sq.c.latest_id)
            .join(Instrument, Opportunity.instrument_id == Instrument.id)
            .join(
                OpportunityScore,
                OpportunityScore.opportunity_id == Opportunity.id,
            )
            .join(
                latest_score_sq,
                (OpportunityScore.opportunity_id == latest_score_sq.c.opportunity_id)
                & (OpportunityScore.scored_at == latest_score_sq.c.max_scored_at),
            )
            .order_by(OpportunityScore.total_score.desc(), Opportunity.detected_at.desc())
            .limit(limit)
        )

        if strategy:
            stmt = stmt.where(Opportunity.strategy == strategy.upper())
        if direction:
            side = OpportunitySide(direction.upper())
            stmt = stmt.where(Opportunity.side == side)
        if grade:
            stmt = stmt.where(
                OpportunityScore.factors["grade"].astext == grade.upper(),
            )

        rows = self._session.execute(stmt).all()
        return [self._row_to_summary(opp, score, inst) for opp, score, inst in rows]

    def get_alerts(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent alerts with opportunity and score details.

        When no rows exist in ``alerts``, falls back to deduplicated approved
        opportunities (the items that would be alerted).
        """
        latest_score_sq = (
            select(
                OpportunityScore.opportunity_id,
                func.max(OpportunityScore.scored_at).label("max_scored_at"),
            )
            .group_by(OpportunityScore.opportunity_id)
            .subquery()
        )

        alert_rows = self._session.execute(
            select(Alert, Opportunity, OpportunityScore, Instrument)
            .join(Opportunity, Alert.opportunity_id == Opportunity.id)
            .join(Instrument, Opportunity.instrument_id == Instrument.id)
            .join(
                OpportunityScore,
                OpportunityScore.opportunity_id == Opportunity.id,
            )
            .join(
                latest_score_sq,
                (OpportunityScore.opportunity_id == latest_score_sq.c.opportunity_id)
                & (OpportunityScore.scored_at == latest_score_sq.c.max_scored_at),
            )
            .order_by(Alert.created_at.desc())
            .limit(limit),
        ).all()

        if alert_rows:
            return [
                self._alert_to_dict(alert, opp, score, inst)
                for alert, opp, score, inst in alert_rows
            ]

        opportunities = self.get_opportunities(limit=limit)
        return [
            {
                "id": item["id"],
                "alert_id": None,
                "time": item["detected_at"],
                "symbol": item["symbol"],
                "strategy": item["strategy"],
                "direction": item["direction"],
                "total_score": item["total_score"],
                "grade": item["grade"],
                "tier": item.get("tier"),
                "channel": None,
                "status": item["status"],
                "scores": item["scores"],
            }
            for item in opportunities
        ]

    def get_opportunity_detail(self, opportunity_id: int) -> dict[str, Any] | None:
        """Return one opportunity with score breakdown and risk decision."""
        stmt = (
            select(Opportunity)
            .options(joinedload(Opportunity.instrument))
            .where(Opportunity.id == opportunity_id)
        )
        opp = self._session.scalar(stmt)
        if opp is None:
            return None

        score_stmt = (
            select(OpportunityScore)
            .where(OpportunityScore.opportunity_id == opportunity_id)
            .order_by(OpportunityScore.scored_at.desc())
            .limit(1)
        )
        score = self._session.scalar(score_stmt)

        risk_stmt = (
            select(RiskDecision)
            .where(RiskDecision.opportunity_id == opportunity_id)
            .order_by(RiskDecision.decided_at.desc())
            .limit(1)
        )
        risk = self._session.scalar(risk_stmt)

        return {
            "id": opp.id,
            "symbol": opp.instrument.inst_id if opp.instrument else None,
            "tier": opp.instrument.tier if opp.instrument else None,
            "strategy": opp.strategy,
            "direction": opp.side.value,
            "status": opp.status.value,
            "entry_price": str(opp.entry_price),
            "detected_at": opp.detected_at.isoformat(),
            "context": opp.context,
            "score": self._score_to_dict(score) if score else None,
            "risk_decision": self._risk_to_dict(risk) if risk else None,
        }

    def get_stats_today(self) -> dict[str, Any]:
        """Aggregate opportunity stats for the current UTC day."""
        today_start = datetime.now(tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )

        base = select(Opportunity).where(
            Opportunity.detected_at >= today_start,
            Opportunity.status == OpportunityStatus.APPROVED,
        )
        total_today = self._session.scalar(
            select(func.count()).select_from(base.subquery()),
        ) or 0

        latest_score_sq = (
            select(
                OpportunityScore.opportunity_id,
                func.max(OpportunityScore.scored_at).label("max_scored_at"),
            )
            .group_by(OpportunityScore.opportunity_id)
            .subquery()
        )

        grade_expr = OpportunityScore.factors["grade"].astext
        grade_rows = self._session.execute(
            select(grade_expr, func.count())
            .join(Opportunity, OpportunityScore.opportunity_id == Opportunity.id)
            .join(
                latest_score_sq,
                (OpportunityScore.opportunity_id == latest_score_sq.c.opportunity_id)
                & (OpportunityScore.scored_at == latest_score_sq.c.max_scored_at),
            )
            .where(
                Opportunity.detected_at >= today_start,
                Opportunity.status == OpportunityStatus.APPROVED,
            )
            .group_by(grade_expr),
        ).all()

        strategy_rows = self._session.execute(
            select(Opportunity.strategy, func.count())
            .where(
                Opportunity.detected_at >= today_start,
                Opportunity.status == OpportunityStatus.APPROVED,
            )
            .group_by(Opportunity.strategy),
        ).all()

        by_grade = {row[0] or "UNKNOWN": row[1] for row in grade_rows}
        by_strategy = {row[0]: row[1] for row in strategy_rows}

        return {
            "total_today": total_today,
            "by_grade": {
                "excellent": by_grade.get("EXCELLENT", 0),
                "good": by_grade.get("GOOD", 0),
                "watch": by_grade.get("WATCH", 0),
            },
            "by_strategy": {
                "funding": by_strategy.get(StrategyType.FUNDING.value, 0),
                "momentum": by_strategy.get(StrategyType.MOMENTUM.value, 0),
            },
        }

    def get_top_opportunities(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """Return top approved opportunities by score."""
        return self.get_opportunities(limit=limit)

    @staticmethod
    def _alert_to_dict(
        alert: Alert,
        opp: Opportunity,
        score: OpportunityScore,
        inst: Instrument,
    ) -> dict[str, Any]:
        summary = OpportunityRepository._row_to_summary(opp, score, inst)
        return {
            "id": opp.id,
            "alert_id": alert.id,
            "time": alert.created_at.isoformat(),
            "symbol": summary["symbol"],
            "strategy": summary["strategy"],
            "direction": summary["direction"],
            "total_score": summary["total_score"],
            "grade": summary["grade"],
            "tier": summary.get("tier"),
            "channel": alert.channel.value,
            "status": alert.status.value,
            "scores": summary["scores"],
        }

    @staticmethod
    def _row_to_summary(
        opp: Opportunity,
        score: OpportunityScore,
        inst: Instrument,
    ) -> dict[str, Any]:
        factors = score.factors or {}
        return {
            "id": opp.id,
            "symbol": inst.inst_id,
            "tier": inst.tier,
            "strategy": opp.strategy,
            "direction": opp.side.value,
            "status": opp.status.value,
            "total_score": score.total_score,
            "grade": factors.get("grade"),
            "detected_at": opp.detected_at.isoformat(),
            "context": opp.context or {},
            "scores": {
                "trend": score.trend_score,
                "momentum": score.momentum_score,
                "volume": score.volume_score,
                "spread": factors.get("spread_score"),
                "liquidity": score.liquidity_score,
                "funding": factors.get("funding_score"),
                "risk_penalty": factors.get("risk_penalty"),
            },
        }

    @staticmethod
    def _score_to_dict(score: OpportunityScore) -> dict[str, Any]:
        factors = score.factors or {}
        return {
            "total_score": score.total_score,
            "grade": factors.get("grade"),
            "model_version": score.model_version,
            "scored_at": score.scored_at.isoformat(),
            "breakdown": {
                "trend_score": score.trend_score,
                "momentum_score": score.momentum_score,
                "volume_score": score.volume_score,
                "spread_score": factors.get("spread_score"),
                "liquidity_score": score.liquidity_score,
                "funding_score": factors.get("funding_score"),
                "risk_penalty": factors.get("risk_penalty"),
            },
        }

    @staticmethod
    def _risk_to_dict(risk: RiskDecision) -> dict[str, Any]:
        return {
            "outcome": risk.outcome.value,
            "reason_code": risk.reason_code,
            "reason_detail": risk.reason_detail,
            "decided_at": risk.decided_at.isoformat(),
            "checks": risk.snapshot,
        }
