"""Unit tests for paper trade repository helpers."""

from __future__ import annotations

from decimal import Decimal

from src.db.models import OpportunitySide
from src.db.repositories.paper_trade import (
    compute_pnl_pct,
    compute_tp_sl_prices,
    tier_config,
)


class TestPaperTradeHelpers:
    def test_tier_config(self) -> None:
        assert tier_config(1)["tp_pct"] == 3.0
        assert tier_config(2)["timeout_hours"] == 12
        assert tier_config(99)["sl_pct"] == 2.5

    def test_long_tp_sl(self) -> None:
        entry = Decimal("100")
        tp, sl = compute_tp_sl_prices(entry, OpportunitySide.LONG, Decimal("3"), Decimal("1.5"))
        assert tp == Decimal("103")
        assert sl == Decimal("98.5")

    def test_short_tp_sl(self) -> None:
        entry = Decimal("100")
        tp, sl = compute_tp_sl_prices(entry, OpportunitySide.SHORT, Decimal("4"), Decimal("2"))
        assert tp == Decimal("96")
        assert sl == Decimal("102")

    def test_long_pnl(self) -> None:
        pnl = compute_pnl_pct(Decimal("100"), Decimal("103"), OpportunitySide.LONG)
        assert pnl == Decimal("3.0000")

    def test_short_pnl(self) -> None:
        pnl = compute_pnl_pct(Decimal("100"), Decimal("97"), OpportunitySide.SHORT)
        assert pnl == Decimal("3.0000")
