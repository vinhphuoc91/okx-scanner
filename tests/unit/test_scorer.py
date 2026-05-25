"""Unit tests for scoring components and OpportunityScorer."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from config.settings import Settings
from src.schemas.market import NormalizedFundingRate, NormalizedTicker
from src.schemas.scoring import Grade
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.scoring.components import (
    score_funding,
    score_liquidity,
    score_momentum,
    score_spread,
    score_trend,
    score_volume,
)
from src.scoring.scorer import OpportunityScorer, classify_grade
from src.strategy.base import MarketContext


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "scoring_grade_excellent": 85,
        "scoring_grade_good": 75,
        "scoring_grade_watch": 65,
        "filter_max_spread_pct": 0.5,
        "risk_max_spread_pct": 0.3,
        "risk_min_volume_usd": 500_000.0,
        "risk_extreme_funding_rate": 0.003,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _ticker(
    *,
    volume: str = "10000000",
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


def _candidate(**signals: object) -> Candidate:
    return Candidate(
        symbol="BTC-USDT-SWAP",
        strategy_type=StrategyType.FUNDING,
        direction=Direction.LONG,
        raw_signals={k: str(v) for k, v in signals.items()},
        detected_at=datetime(2026, 5, 25, tzinfo=UTC),
        confidence=0.8,
    )


@pytest.mark.unit
class TestScoreComponents:
    def test_score_trend_with_ema(self) -> None:
        result = score_trend(
            {"ema_fast": "105", "ema_slow": "100", "uptrend": True},
        )
        assert 0.0 < result <= 25.0

    def test_score_trend_missing_data(self) -> None:
        assert score_trend({}) == 0.0

    def test_score_momentum_bullish(self) -> None:
        result = score_momentum({"rsi": "65", "rsi_bullish": True})
        assert 0.0 < result <= 20.0

    def test_score_liquidity_tiers(self) -> None:
        high = score_liquidity(_ticker(volume="20000000"))
        low = score_liquidity(_ticker(volume="100000"))
        assert high > low

    def test_score_volume_ratio(self) -> None:
        result = score_volume(_ticker(), signals={"volume_ratio": 2.0})
        assert result == 15.0

    def test_score_funding_magnitude(self) -> None:
        fr = NormalizedFundingRate(
            inst_id="BTC-USDT-SWAP",
            funding_rate=Decimal("-0.001"),
            funding_time=datetime(2026, 5, 25, tzinfo=UTC),
        )
        assert score_funding(fr) > 0.0

    def test_score_spread_tight(self) -> None:
        assert score_spread(_ticker(bid="100", ask="100.01")) > 5.0


@pytest.mark.unit
class TestOpportunityScorer:
    def test_score_in_range(self) -> None:
        scorer = OpportunityScorer(settings=_settings(), persist=False)
        ctx = MarketContext(
            ticker=_ticker(),
            funding_rate=NormalizedFundingRate(
                inst_id="BTC-USDT-SWAP",
                funding_rate=Decimal("-0.0005"),
                funding_time=datetime(2026, 5, 25, tzinfo=UTC),
            ),
        )
        cand = _candidate(
            spread_pct="0.05",
            volume_24h_usd="10000000",
            funding_rate="-0.0005",
        )
        result = scorer.score(cand, ctx)
        assert 0 <= result.total_score <= 100

    def test_deterministic(self) -> None:
        scorer = OpportunityScorer(settings=_settings(), persist=False)
        ctx = MarketContext(
            ticker=_ticker(),
            funding_rate=NormalizedFundingRate(
                inst_id="BTC-USDT-SWAP",
                funding_rate=Decimal("-0.0005"),
                funding_time=datetime(2026, 5, 25, tzinfo=UTC),
            ),
        )
        cand = _candidate(spread_pct="0.05", funding_rate="-0.0005")
        r1 = scorer.score(cand, ctx)
        r2 = scorer.score(cand, ctx)
        assert r1 == r2

    @pytest.mark.parametrize(
        ("total", "expected"),
        [
            (90, Grade.EXCELLENT),
            (80, Grade.GOOD),
            (70, Grade.WATCH),
            (50, Grade.IGNORE),
        ],
    )
    def test_grade_classification(self, total: int, expected: Grade) -> None:
        assert classify_grade(total, _settings()) == expected

    def test_funding_strategy_ignores_trend_momentum(self) -> None:
        scorer = OpportunityScorer(settings=_settings(), persist=False)
        ctx = MarketContext(
            ticker=_ticker(volume="20000000"),
            funding_rate=NormalizedFundingRate(
                inst_id="BTC-USDT-SWAP",
                funding_rate=Decimal("-0.001"),
                funding_time=datetime(2026, 5, 25, tzinfo=UTC),
            ),
        )
        cand = _candidate(spread_pct="0.05", funding_rate="-0.001")
        result = scorer.score(cand, ctx)
        assert result.breakdown.trend_score == 0.0
        assert result.breakdown.momentum_score == 0.0
        assert result.breakdown.funding_score > 0.0
        assert result.total_score >= 65

    def test_momentum_strategy_ignores_funding(self) -> None:
        scorer = OpportunityScorer(settings=_settings(), persist=False)
        ctx = MarketContext(
            ticker=_ticker(volume="20000000"),
            funding_rate=NormalizedFundingRate(
                inst_id="BTC-USDT-SWAP",
                funding_rate=Decimal("-0.001"),
                funding_time=datetime(2026, 5, 25, tzinfo=UTC),
            ),
        )
        cand = Candidate(
            symbol="BTC-USDT-SWAP",
            strategy_type=StrategyType.MOMENTUM,
            direction=Direction.LONG,
            raw_signals={
                "ema_fast": "105",
                "ema_slow": "100",
                "uptrend": True,
                "rsi": "65",
                "rsi_bullish": True,
                "volume_ratio": "2.0",
            },
            detected_at=datetime(2026, 5, 25, tzinfo=UTC),
            confidence=0.8,
        )
        result = scorer.score(cand, ctx)
        assert result.breakdown.funding_score == 0.0
        assert result.breakdown.trend_score > 0.0
        assert result.breakdown.momentum_score > 0.0
