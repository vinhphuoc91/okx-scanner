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


@router.get("/balance")
def get_balance(session: Session = Depends(get_db)):
    cfg = TradingConfigRepository(session).get()
    if not cfg.api_key:
        raise HTTPException(status_code=400, detail="API credentials not configured")
    client = OKXTradingClient(cfg.api_key, cfg.api_secret, cfg.api_passphrase)
    bal = client.get_balance()
    return {"available": float(bal["available"]), "total": float(bal["total"])}


@router.get("/daily-risk")
def get_daily_risk(session: Session = Depends(get_db)):
    from datetime import datetime, timezone

    from src.db.models import PaperTrade, PaperTradeStatus
    from src.risk.real_trade_risk import RealTradeRiskGate

    gate = RealTradeRiskGate(session)
    cfg = gate.get_config()
    today = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    losses = session.query(PaperTrade).filter(
        PaperTrade.mode == "real",
        PaperTrade.closed_at >= today,
        PaperTrade.status == PaperTradeStatus.LOSS,
    ).all()
    loss_pct = sum(abs(float(t.pnl_pct)) for t in losses if t.pnl_pct)
    limit = cfg.daily_loss_limit_pct
    return {
        "daily_loss_pct": round(loss_pct, 2),
        "daily_loss_limit_pct": limit,
        "remaining_pct": round(max(0, limit - loss_pct), 2),
        "is_blocked": loss_pct >= limit,
    }


@router.get("/strategy-toggles")
def get_strategy_toggles(session: Session = Depends(get_db)):
    from src.db.repositories.strategy_settings import StrategySettingsRepository

    settings = StrategySettingsRepository(session).get_all_settings()
    return [{"strategy_type": k, "real_trading_enabled": v.real_trading_enabled} for k, v in settings.items()]


class StrategyToggleUpdate(BaseModel):
    real_trading_enabled: bool = False


@router.put("/strategy-toggles/{strategy}")
def update_strategy_toggle(
    strategy: str,
    body: StrategyToggleUpdate,
    session: Session = Depends(get_db),
):
    from src.db.repositories.strategy_settings import StrategySettingsRepository

    repo = StrategySettingsRepository(session)
    repo.update_settings(strategy, real_trading_enabled=body.real_trading_enabled)
    session.commit()
    return {"ok": True}
