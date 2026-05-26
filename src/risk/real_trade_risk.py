"""Real trading risk gate — daily loss limit + position size calculator."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from src.db.models import PaperTrade, PaperTradeStatus, TradingConfig
from src.db.repositories.trading_config import TradingConfigRepository
from src.collector.trading_client import OKXTradingClient
from src.utils.logger import get_logger

log = get_logger(__name__)


class RealTradeRiskGate:
    """Check daily loss limit and compute position size before placing real orders."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = TradingConfigRepository(session)

    def get_config(self) -> TradingConfig:
        return self._repo.get()

    def is_real_mode(self) -> bool:
        return self.get_config().mode == "real"

    def check_daily_loss(self) -> tuple[bool, str]:
        """Return (ok, reason). Blocks trading if daily loss limit exceeded."""
        cfg = self.get_config()
        if not cfg.api_key or not cfg.api_secret or not cfg.api_passphrase:
            return False, "api_credentials_missing"

        client = OKXTradingClient(cfg.api_key, cfg.api_secret, cfg.api_passphrase)
        balance = client.get_balance()
        total = balance["total"]
        if total <= 0:
            return False, "zero_balance"

        # Sum today's closed real trade losses
        today_start = datetime.now(tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_trades = (
            self._session.query(PaperTrade)
            .filter(
                PaperTrade.mode == "real",
                PaperTrade.closed_at >= today_start,
                PaperTrade.status == PaperTradeStatus.LOSS,
                PaperTrade.pnl_pct.isnot(None),
            )
            .all()
        )
        total_loss_pct = sum(abs(float(t.pnl_pct)) for t in today_trades if t.pnl_pct < 0)

        limit = cfg.daily_loss_limit_pct
        if total_loss_pct >= limit:
            log.warning(
                "real_risk.daily_loss_limit_hit",
                total_loss_pct=total_loss_pct,
                limit=limit,
            )
            return False, f"daily_loss_limit_hit:{total_loss_pct:.1f}%>={limit}%"

        log.info("real_risk.daily_loss_ok", total_loss_pct=total_loss_pct, limit=limit)
        return True, "ok"

    def compute_position_size(self, *, tier: int, entry_price: Decimal) -> Decimal:
        """Return position size in USDT based on tier and account balance."""
        cfg = self.get_config()
        if not cfg.api_key:
            return Decimal("0")

        client = OKXTradingClient(cfg.api_key, cfg.api_secret, cfg.api_passphrase)
        balance = client.get_balance()
        available = balance["available"]

        pct_map = {1: cfg.size_pct_tier1, 2: cfg.size_pct_tier2, 3: cfg.size_pct_tier3}
        pct = Decimal(str(pct_map.get(tier, cfg.size_pct_tier3)))
        size_usdt = (available * pct / Decimal("100")).quantize(Decimal("0.01"))

        log.info(
            "real_risk.position_size",
            tier=tier,
            available_usdt=str(available),
            size_pct=str(pct),
            size_usdt=str(size_usdt),
        )
        return size_usdt

    def can_trade(self, *, tier: int, strategy: str, entry_price: Decimal) -> tuple[bool, str, Decimal]:
        """Full pre-trade check. Returns (allowed, reason, size_usdt)."""
        if not self.is_real_mode():
            return False, "paper_mode", Decimal("0")

        ok, reason = self.check_daily_loss()
        if not ok:
            return False, reason, Decimal("0")

        size = self.compute_position_size(tier=tier, entry_price=entry_price)
        if size <= 0:
            return False, "insufficient_balance", Decimal("0")

        return True, "ok", size
