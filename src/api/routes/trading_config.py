"""API routes for trading config — GET/PUT /trading/config, POST /trading/test-connection."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.collector.trading_client import OKXTradingClient
from src.db.repositories.trading_config import TradingConfigRepository
from src.db.session import get_db

router = APIRouter(prefix="/trading", tags=["trading"])


class TradingConfigUpdate(BaseModel):
    mode: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    daily_loss_limit_pct: float | None = None
    size_pct_tier1: float | None = None
    size_pct_tier2: float | None = None
    size_pct_tier3: float | None = None
    max_leverage: int | None = None


@router.get("/config")
def get_trading_config(session: Session = Depends(get_db)):
    repo = TradingConfigRepository(session)
    return TradingConfigRepository.to_dict(repo.get())


@router.put("/config")
def update_trading_config(body: TradingConfigUpdate, session: Session = Depends(get_db)):
    repo = TradingConfigRepository(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "mode" in updates and updates["mode"] not in ("paper", "real"):
        raise HTTPException(status_code=400, detail="mode must be 'paper' or 'real'")
    row = repo.update(**updates)
    session.commit()
    return TradingConfigRepository.to_dict(row)


@router.post("/test-connection")
def test_connection(session: Session = Depends(get_db)):
    repo = TradingConfigRepository(session)
    cfg = repo.get()
    if not cfg.api_key or not cfg.api_secret or not cfg.api_passphrase:
        raise HTTPException(status_code=400, detail="API credentials not configured")
    client = OKXTradingClient(cfg.api_key, cfg.api_secret, cfg.api_passphrase)
    ok = client.test_connection()
    return {"success": ok, "message": "Connected successfully" if ok else "Connection failed"}
