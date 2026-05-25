"""Paper trade alerts and performance API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.repositories.paper_trade import PaperTradeRepository
from src.db.session import get_db
from src.worker.pending_confirmations import PendingConfirmationStore

router = APIRouter(tags=["alerts"])
_pending_store = PendingConfirmationStore()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.get("/alerts")
def list_alerts(
    limit: int = Query(100, ge=1, le=500),
    status: str | None = Query(None, description="RUNNING | WIN | LOSS | EXPIRED"),
    strategy: str | None = Query(None, description="FUNDING | MOMENTUM | BREAKOUT | ..."),
    tier: int | None = Query(None, ge=1, le=3),
    direction: str | None = Query(None, description="LONG | SHORT"),
    date_from: str | None = Query(None, description="ISO datetime lower bound"),
    date_to: str | None = Query(None, description="ISO datetime upper bound"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return paper trades with optional filters."""
    repo = PaperTradeRepository(db)
    items = repo.get_trades(
        limit=limit,
        status=status,
        strategy=strategy,
        tier=tier,
        direction=direction,
        date_from=_parse_datetime(date_from),
        date_to=_parse_datetime(date_to),
    )
    return {"count": len(items), "items": items}


@router.get("/alerts/pending")
def list_pending_confirmations() -> dict[str, Any]:
    """Return opportunities awaiting M15 confirmation."""
    store = PendingConfirmationStore()
    items = [store.pending_to_dict(p) for p in store.list_all()]
    return {"count": len(items), "items": items}


@router.get("/alerts/confirm-failed")
def list_confirm_failed(
    limit: int = Query(100, ge=1, le=500),
    strategy: str | None = Query(None),
    tier: int | None = Query(None, ge=1, le=3),
    direction: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return opportunities that failed M15 confirmation."""
    repo = PaperTradeRepository(db)
    items = repo.get_confirm_failed(
        limit=limit,
        strategy=strategy,
        tier=tier,
        direction=direction,
        date_from=_parse_datetime(date_from),
        date_to=_parse_datetime(date_to),
    )
    return {"count": len(items), "items": items}


@router.get("/alerts/stats")
def alert_stats(
    date_from: str | None = Query(None, description="ISO datetime lower bound (entry_at)"),
    date_to: str | None = Query(None, description="ISO datetime upper bound (entry_at)"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return aggregated paper trade performance statistics."""
    repo = PaperTradeRepository(db)
    return repo.get_stats(
        date_from=_parse_datetime(date_from),
        date_to=_parse_datetime(date_to),
    )
