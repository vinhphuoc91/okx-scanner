"""Score repository — read opportunity scores."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import OpportunityScore


class ScoreRepository:
    """Read helpers for :class:`~src.db.models.OpportunityScore`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_score_by_opportunity(self, opportunity_id: int) -> OpportunityScore | None:
        """Return the latest score row for *opportunity_id*."""
        stmt = (
            select(OpportunityScore)
            .where(OpportunityScore.opportunity_id == opportunity_id)
            .order_by(OpportunityScore.scored_at.desc())
            .limit(1)
        )
        return self._session.scalar(stmt)
