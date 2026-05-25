"""Scanner status and statistics API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.repositories.opportunity import OpportunityRepository
from src.db.session import get_db
from src.worker.scanner_state import ScannerState

router = APIRouter(tags=["status"])


@router.get("/status")
def scanner_status() -> dict[str, Any]:
    """Return scanner worker liveness and per-tier last scan times."""
    state = ScannerState().get_status()
    return {
        "scanner_running": state["running"],
        "started_at": state["started_at"],
        "heartbeat_at": state["heartbeat_at"],
        "uptime_seconds": state["uptime_seconds"],
        "last_scan_by_tier": state["last_scan_by_tier"],
        "worker_totals": state["totals"],
    }


@router.get("/stats")
def scanner_stats(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return today's opportunity stats and top opportunities."""
    repo = OpportunityRepository(db)
    today = repo.get_stats_today()
    top = repo.get_top_opportunities(limit=10)
    return {
        **today,
        "top_opportunities": top,
    }
