"""Opportunity read-only API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.db.repositories.opportunity import OpportunityRepository
from src.db.session import get_db

router = APIRouter(tags=["opportunities"])


@router.get("/opportunities")
def list_opportunities(
    grade: str | None = Query(None, description="EXCELLENT | GOOD | WATCH"),
    strategy: str | None = Query(None, description="FUNDING | MOMENTUM"),
    direction: str | None = Query(None, description="LONG | SHORT"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List approved opportunities with latest scores."""
    repo = OpportunityRepository(db)
    items = repo.get_opportunities(
        grade=grade,
        strategy=strategy,
        direction=direction,
        limit=limit,
    )
    return {"count": len(items), "items": items}


@router.get("/opportunities/{opportunity_id}")
def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return one opportunity with score breakdown and risk decision."""
    repo = OpportunityRepository(db)
    detail = repo.get_opportunity_detail(opportunity_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_id} not found",
        )
    return detail
