"""Unit tests for MarketFilter."""

from __future__ import annotations

from datetime import datetime, timedelta

from src.utils.compat import UTC
from decimal import Decimal

import pytest

from config.settings import Settings
from src.filter.market_filter import MarketFilter
from src.schemas.market import NormalizedInstrument, NormalizedTicker


def _settings(**overrides: object) -> Settings:
    """Build a Settings instance with filter-friendly defaults (no .env)."""
    base: dict[str, object] = {
        "filter_min_volume_usd": 1_000_000.0,
        "filter_max_spread_pct": 0.5,
        "filter_min_listing_age_days": 7,
        "filter_quote_currencies": "USDT",
        "filter_inst_types": "SPOT,SWAP",
        "filter_tier1_size": 50,
        "filter_tier2_size": 200,
        "filter_tier1_interval_seconds": 60,
        "filter_tier2_interval_seconds": 300,
        "filter_tier3_interval_seconds": 900,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _ticker(
    inst_id: str,
    *,
    volume_quote: str = "5000000",
    bid: str = "100",
    ask: str = "100.1",
    last: str = "100.05",
) -> NormalizedTicker:
    return NormalizedTicker(
        inst_id=inst_id,
        last_price=Decimal(last),
        bid_price=Decimal(bid),
        ask_price=Decimal(ask),
        volume_24h_quote=Decimal(volume_quote),
    )


@pytest.fixture
def reference_time() -> datetime:
    return datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def market_filter(reference_time: datetime) -> MarketFilter:
    return MarketFilter(settings=_settings(), reference_time=reference_time)


@pytest.mark.unit
class TestMarketFilterVolume:
    def test_rejects_low_volume(self, market_filter: MarketFilter) -> None:
        tickers = [_ticker("LOW-USDT", volume_quote="500000")]
        result = market_filter.filter_instruments(tickers)
        assert len(result.passed) == 0
        assert len(result.rejected) == 1
        assert any("volume_below_min" in r for r in result.rejected[0].reasons)

    def test_passes_high_volume(self, market_filter: MarketFilter) -> None:
        tickers = [_ticker("BTC-USDT", volume_quote="10000000")]
        result = market_filter.filter_instruments(tickers)
        assert len(result.passed) == 1
        assert result.passed[0].inst_id == "BTC-USDT"


@pytest.mark.unit
class TestMarketFilterSpread:
    def test_rejects_wide_spread(self, market_filter: MarketFilter) -> None:
        tickers = [_ticker("WIDE-USDT", bid="100", ask="102")]
        result = market_filter.filter_instruments(tickers)
        assert len(result.passed) == 0
        assert any("spread_above_max" in r for r in result.rejected[0].reasons)

    def test_rejects_missing_spread(self, market_filter: MarketFilter) -> None:
        tickers = [
            NormalizedTicker(
                inst_id="NOSPREAD-USDT",
                last_price=Decimal("100"),
                volume_24h_quote=Decimal("5000000"),
            ),
        ]
        result = market_filter.filter_instruments(tickers)
        assert any("missing_or_invalid_spread" in r for r in result.rejected[0].reasons)


@pytest.mark.unit
class TestMarketFilterRules:
    def test_rejects_non_usdt_pair(self, market_filter: MarketFilter) -> None:
        tickers = [_ticker("BTC-USDC")]
        result = market_filter.filter_instruments(tickers)
        assert any("not_usdt_pair" in r for r in result.rejected[0].reasons)

    def test_rejects_disallowed_inst_type(self, reference_time: datetime) -> None:
        mf = MarketFilter(
            settings=_settings(filter_inst_types="SPOT"),
            reference_time=reference_time,
        )
        tickers = [_ticker("ETH-USDT-SWAP")]
        result = mf.filter_instruments(tickers)
        assert any("inst_type_not_allowed" in r for r in result.rejected[0].reasons)

    def test_rejects_new_listing(self, reference_time: datetime) -> None:
        meta = {
            "NEW-USDT": NormalizedInstrument(
                inst_id="NEW-USDT",
                inst_type="SPOT",
                base_ccy="NEW",
                quote_ccy="USDT",
                tick_size=Decimal("0.01"),
                lot_size=Decimal("1"),
                min_size=Decimal("1"),
                listed_at=reference_time - timedelta(days=2),
            ),
        }
        mf = MarketFilter(
            settings=_settings(),
            instrument_metadata=meta,
            reference_time=reference_time,
        )
        result = mf.filter_instruments([_ticker("NEW-USDT")])
        assert any("listing_too_new" in r for r in result.rejected[0].reasons)

    def test_accepts_usdt_swap(self, market_filter: MarketFilter) -> None:
        tickers = [_ticker("BTC-USDT-SWAP")]
        result = market_filter.filter_instruments(tickers)
        assert len(result.passed) == 1
        assert result.passed[0].inst_type == "SWAP"


@pytest.mark.unit
class TestTierAssignment:
    def test_tier_boundaries(self, market_filter: MarketFilter) -> None:
        tickers = [
            _ticker(f"PAIR{i}-USDT", volume_quote=str(10_000_000 - i * 1000))
            for i in range(210)
        ]
        result = market_filter.filter_instruments(tickers)
        tiered = market_filter.assign_tiers(list(result.passed))

        assert len(tiered.tier1) == 50
        assert len(tiered.tier2) == 150
        assert len(tiered.tier3) == 10

    def test_tier1_highest_volume(self, market_filter: MarketFilter) -> None:
        tickers = [
            _ticker("LOW-USDT", volume_quote="2000000"),
            _ticker("HIGH-USDT", volume_quote="9000000"),
            _ticker("MID-USDT", volume_quote="5000000"),
        ]
        passed = list(market_filter.filter_instruments(tickers).passed)
        tiered = market_filter.assign_tiers(passed)

        assert tiered.tier1[0].inst_id == "HIGH-USDT"
        assert tiered.tier1[0].tier == 1
        assert tiered.tier1[0].scan_interval_seconds == 60

    def test_tier2_interval(self, market_filter: MarketFilter) -> None:
        tickers = [
            _ticker(f"P{i}-USDT", volume_quote=str(5_000_000 - i))
            for i in range(55)
        ]
        passed = list(market_filter.filter_instruments(tickers).passed)
        tiered = market_filter.assign_tiers(passed)
        assert tiered.tier2[0].tier == 2
        assert tiered.tier2[0].scan_interval_seconds == 300

    def test_tier3_interval(self, market_filter: MarketFilter) -> None:
        tickers = [
            _ticker(f"P{i}-USDT", volume_quote=str(5_000_000 - i))
            for i in range(205)
        ]
        passed = list(market_filter.filter_instruments(tickers).passed)
        tiered = market_filter.assign_tiers(passed)
        assert tiered.tier3[0].tier == 3
        assert tiered.tier3[0].scan_interval_seconds == 900


@pytest.mark.unit
class TestDeterminismAndEdgeCases:
    def test_deterministic_output(self, market_filter: MarketFilter) -> None:
        tickers = [
            _ticker("B-USDT", volume_quote="5000000"),
            _ticker("A-USDT", volume_quote="5000000"),
            _ticker("C-USDT", volume_quote="3000000"),
        ]
        result1 = market_filter.filter_instruments(tickers)
        result2 = market_filter.filter_instruments(tickers)
        assert result1 == result2

        tiered1 = market_filter.assign_tiers(list(result1.passed))
        tiered2 = market_filter.assign_tiers(list(result2.passed))
        assert tiered1 == tiered2

    def test_empty_input(self, market_filter: MarketFilter) -> None:
        result = market_filter.filter_instruments([])
        assert result.passed == ()
        assert result.rejected == ()
        tiered = market_filter.assign_tiers([])
        assert tiered.tier1 == tiered.tier2 == tiered.tier3 == ()

    def test_all_filtered_out(self, market_filter: MarketFilter) -> None:
        tickers = [_ticker("LOW-USDT", volume_quote="100")]
        result = market_filter.filter_instruments(tickers)
        assert len(result.passed) == 0
        tiered = market_filter.assign_tiers(list(result.passed))
        assert len(tiered.tier1) == len(tiered.tier2) == len(tiered.tier3) == 0

    def test_volume_tie_breaks_by_inst_id(self, market_filter: MarketFilter) -> None:
        tickers = [
            _ticker("Z-USDT", volume_quote="8000000"),
            _ticker("A-USDT", volume_quote="8000000"),
        ]
        passed = list(market_filter.filter_instruments(tickers).passed)
        tiered = market_filter.assign_tiers(passed)
        assert tiered.tier1[0].inst_id == "A-USDT"
        assert tiered.tier1[1].inst_id == "Z-USDT"
