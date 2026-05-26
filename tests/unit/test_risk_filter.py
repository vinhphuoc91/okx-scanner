"""Unit tests for RiskFilter hard-reject rules."""

from __future__ import annotations

from datetime import datetime

from src.utils.compat import UTC
from decimal import Decimal

import pytest

from config.settings import Settings
from src.risk.risk_filter import RiskFilter
from src.schemas.market import NormalizedFundingRate, NormalizedTicker
from src.schemas.risk import RejectionCode
from src.schemas.scoring import Grade, ScoreBreakdown, ScoredOpportunity
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.strategy.base import MarketContext


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "risk_max_spread_pct": 0.3,
        "risk_min_volume_usd": 500_000.0,
        "risk_extreme_funding_rate": 0.003,
        "alert_min_score": 65,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _ticker(
    *,
    volume: str = "5000000",
    bid: str = "100",
    ask: str = "100.05",
) -> NormalizedTicker:
    return NormalizedTicker(
        inst_id="BTC-USDT-SWAP",
        last_price=Decimal("100.025"),
        bid_price=Decimal(bid),
        ask_price=Decimal(ask),
        volume_24h_quote=Decimal(volume),
    )


def _scored(total: int = 80) -> ScoredOpportunity:
    return ScoredOpportunity(
        candidate=Candidate(
            symbol="BTC-USDT-SWAP",
            strategy_type=StrategyType.FUNDING,
            direction=Direction.LONG,
            raw_signals={"spread_pct": "0.05"},
            detected_at=datetime(2026, 5, 25, tzinfo=UTC),
            confidence=0.8,
        ),
        breakdown=ScoreBreakdown(
            trend_score=0,
            momentum_score=0,
            liquidity_score=10,
            volume_score=5,
            funding_score=10,
            spread_score=8,
            risk_penalty=0,
        ),
        total_score=total,
        grade=Grade.GOOD,
    )


def _ctx(
    *,
    volume: str = "5000000",
    bid: str = "100",
    ask: str = "100.05",
    funding: str = "-0.0005",
) -> MarketContext:
    return MarketContext(
        ticker=_ticker(volume=volume, bid=bid, ask=ask),
        funding_rate=NormalizedFundingRate(
            inst_id="BTC-USDT-SWAP",
            funding_rate=Decimal(funding),
            funding_time=datetime(2026, 5, 25, tzinfo=UTC),
        ),
    )


@pytest.fixture
def risk_filter() -> RiskFilter:
    return RiskFilter(settings=_settings(), persist=False)


@pytest.mark.unit
class TestRiskFilterApprove:
    def test_approve_when_all_rules_pass(self, risk_filter: RiskFilter) -> None:
        decision = risk_filter.evaluate(_scored(80), _ctx())
        assert decision.approved is True
        assert decision.rejection_codes == ()


@pytest.mark.unit
class TestRiskFilterReject:
    def test_reject_spread_too_high(self, risk_filter: RiskFilter) -> None:
        decision = risk_filter.evaluate(
            _scored(80),
            _ctx(bid="100", ask="101"),
        )
        assert not decision.approved
        assert RejectionCode.SPREAD_TOO_HIGH in decision.rejection_codes

    def test_reject_low_volume(self, risk_filter: RiskFilter) -> None:
        decision = risk_filter.evaluate(_scored(80), _ctx(volume="100000"))
        assert not decision.approved
        assert RejectionCode.LOW_VOLUME in decision.rejection_codes

    def test_reject_extreme_funding(self, risk_filter: RiskFilter) -> None:
        decision = risk_filter.evaluate(_scored(80), _ctx(funding="-0.005"))
        assert not decision.approved
        assert RejectionCode.EXTREME_FUNDING in decision.rejection_codes

    def test_reject_score_too_low(self, risk_filter: RiskFilter) -> None:
        decision = risk_filter.evaluate(_scored(50), _ctx())
        assert not decision.approved
        assert RejectionCode.SCORE_TOO_LOW in decision.rejection_codes

    def test_approved_never_violates_hard_rules(self, risk_filter: RiskFilter) -> None:
        decision = risk_filter.evaluate(_scored(90), _ctx())
        assert decision.approved
        checks = decision.raw_checks
        assert checks["spread_pct"] <= checks["max_spread_pct"]
        assert checks["volume_24h_usd"] >= checks["min_volume_usd"]
        assert checks["funding_magnitude"] <= checks["extreme_funding_rate"]
        assert checks["total_score"] >= checks["alert_min_score"]
