"""Unit tests for StatArbitrageStrategy."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from config.settings import Settings
from src.schemas.market import NormalizedFundingRate, NormalizedTicker
from src.schemas.strategy import Direction, StrategyType
from src.strategy.base import MarketContext
from src.strategy.helpers import basis_trend, calc_basis_pct
from src.strategy.stat_arb import StatArbitrageStrategy


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "stat_arb_min_basis": 0.2,
        "stat_arb_strong_basis": 0.5,
        "stat_arb_basis_trend_periods": 5,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


@pytest.fixture
def strategy() -> StatArbitrageStrategy:
    return StatArbitrageStrategy(settings=_settings())


@pytest.mark.unit
class TestStatArbitrageStrategy:
    def test_calc_basis(self) -> None:
        basis = calc_basis_pct(Decimal("67000"), Decimal("67350"))
        assert basis is not None
        assert round(basis, 2) == 0.52

    def test_basis_trend(self) -> None:
        assert basis_trend([0.6, 0.5, 0.4, 0.35, 0.3]) == pytest.approx(-0.3)

    def test_high_basis_short(self, strategy: StatArbitrageStrategy) -> None:
        ctx = MarketContext(
            symbol="BTC-USDT-SWAP",
            ticker=NormalizedTicker(inst_id="BTC-USDT-SWAP", last_price=Decimal("67350")),
            spot_ticker=NormalizedTicker(inst_id="BTC-USDT", last_price=Decimal("67000")),
            funding_rate=NormalizedFundingRate(
                inst_id="BTC-USDT-SWAP",
                funding_rate=Decimal("0.0003"),
                funding_time=datetime.now(tz=UTC),
            ),
            basis_history_pct=[0.6, 0.55, 0.52, 0.51, 0.5],
        )
        results = strategy.scan(ctx)
        assert len(results) == 1
        assert results[0].direction == Direction.SHORT
        assert results[0].strategy_type == StrategyType.STAT_ARBITRAGE
        assert float(results[0].raw_signals["basis_pct"]) >= 0.2

    def test_low_basis_long(self, strategy: StatArbitrageStrategy) -> None:
        ctx = MarketContext(
            symbol="BTC-USDT-SWAP",
            ticker=NormalizedTicker(inst_id="BTC-USDT-SWAP", last_price=Decimal("66800")),
            spot_ticker=NormalizedTicker(inst_id="BTC-USDT", last_price=Decimal("67000")),
            basis_history_pct=[-0.1, -0.25, -0.3],
        )
        results = strategy.scan(ctx)
        assert len(results) == 1
        assert results[0].direction == Direction.LONG

    def test_skip_without_spot(self, strategy: StatArbitrageStrategy) -> None:
        ctx = MarketContext(
            symbol="BTC-USDT-SWAP",
            ticker=NormalizedTicker(inst_id="BTC-USDT-SWAP", last_price=Decimal("67350")),
        )
        assert strategy.scan(ctx) == []
