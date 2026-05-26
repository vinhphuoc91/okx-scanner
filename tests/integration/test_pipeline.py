"""Integration tests for the full scanner pipeline."""

from __future__ import annotations

import signal
import threading
import time
from datetime import datetime

from src.utils.compat import UTC
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings
from src.db.models import Instrument, InstrumentType
from src.schemas.strategy import Direction, StrategyType
from src.worker.scanner_loop import ScannerLoop
from src.worker.scheduler import TierScheduler


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "filter_min_volume_usd": 500_000.0,
        "filter_max_spread_pct": 0.5,
        "filter_tier1_size": 10,
        "filter_tier2_size": 20,
        "filter_tier1_interval_seconds": 60,
        "filter_tier2_interval_seconds": 300,
        "filter_tier3_interval_seconds": 900,
        "funding_rate_long_threshold": -0.0001,
        "funding_rate_short_threshold": 0.0005,
        "alert_min_score": 50,
        "risk_max_spread_pct": 0.5,
        "risk_min_volume_usd": 500_000.0,
        "risk_extreme_funding_rate": 0.01,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def _swap_ticker(inst_id: str = "BTC-USDT-SWAP") -> dict:
    return {
        "instId": inst_id,
        "instType": "SWAP",
        "last": "100",
        "bidPx": "99.95",
        "askPx": "100.05",
        "volCcy24h": "10000000",
        "ts": str(int(datetime.now(tz=UTC).timestamp() * 1000)),
    }


def _funding_row(inst_id: str = "BTC-USDT-SWAP") -> dict:
    return {
        "instId": inst_id,
        "fundingRate": "-0.0005",
        "fundingTime": str(int(datetime.now(tz=UTC).timestamp() * 1000)),
    }


def _make_instrument(inst_id: str = "BTC-USDT-SWAP", tier: int = 1) -> Instrument:
    return Instrument(
        id=1,
        inst_id=inst_id,
        inst_type=InstrumentType.SWAP,
        base_ccy="BTC",
        quote_ccy="USDT",
        tick_size=Decimal("0.01"),
        lot_size=Decimal("0.001"),
        min_size=Decimal("0.001"),
        is_active=True,
        tier=tier,
        scan_interval_seconds=60,
    )


def _mock_strategy_settings_repo() -> MagicMock:
    """Strategy settings repo with all strategies enabled."""
    mock_cfg = MagicMock()
    mock_cfg.is_enabled = True
    mock_cfg.min_score = 50
    mock_cfg.requires_confirmation = False
    mock_cfg.confirmation_candles = 1
    mock_cfg.tier_atr_params.return_value = {
        "sl_multiplier": 1.5,
        "tp_multiplier": 3.0,
        "timeout_hours": 8,
    }

    mock_global = MagicMock()
    mock_global.alert_min_score = 50

    mock_repo = MagicMock()
    mock_repo.get_all_settings.return_value = {
        "FUNDING": mock_cfg,
        "MOMENTUM": mock_cfg,
        "BREAKOUT": mock_cfg,
        "VOLUME_ANOMALY": mock_cfg,
        "TREND_PULLBACK": mock_cfg,
    }
    mock_repo.get_global_config.return_value = mock_global
    mock_repo.get_settings.return_value = mock_cfg
    return mock_repo


@pytest.mark.integration
class TestScannerPipeline:
    def test_full_cycle_with_mock_okx(self) -> None:
        mock_client = MagicMock()
        mock_client.get_tickers.return_value = [_swap_ticker()]
        mock_client.get_funding_rates.return_value = [_funding_row()]
        mock_client.get_candles.return_value = []

        mock_session = MagicMock()
        instrument = _make_instrument()

        mock_instrument_repo = MagicMock()
        mock_instrument_repo.get_instruments_by_tier.return_value = [instrument]
        mock_instrument_repo.update_instrument_tier.return_value = instrument

        mock_scorer = MagicMock()
        mock_scored = MagicMock()
        mock_scored.total_score = 80
        mock_scored.grade.value = "GOOD"
        mock_scored.opportunity_id = 1
        mock_scored.candidate.symbol = "BTC-USDT-SWAP"
        mock_scored.candidate.strategy_type = StrategyType.FUNDING
        mock_scored.candidate.direction = Direction.LONG
        mock_scorer.score.return_value = mock_scored

        mock_risk = MagicMock()
        mock_decision = MagicMock()
        mock_decision.approved = True
        mock_decision.rejection_codes = ()
        mock_risk.evaluate.return_value = mock_decision

        mock_state = MagicMock()
        settings = _settings()

        def session_factory():
            return mock_session

        loop = ScannerLoop(
            settings=settings,
            client=mock_client,
            session_factory=session_factory,
            scheduler=TierScheduler(settings=settings),
            state=mock_state,
        )

        with (
            patch("src.worker.scanner_loop.InstrumentRepository", return_value=mock_instrument_repo),
            patch("src.worker.scanner_loop.OpportunityScorer", return_value=mock_scorer),
            patch("src.worker.scanner_loop.RiskFilter", return_value=mock_risk),
            patch("src.worker.scanner_loop.StrategySettingsRepository", return_value=_mock_strategy_settings_repo()),
            patch("src.worker.scanner_loop.FundingStrategy") as mock_funding_cls,
            patch("src.worker.trade_tracker.PaperTradeRepository") as mock_trade_repo_cls,
            patch("src.worker.trade_tracker.OpportunityRepository") as mock_opp_repo_cls,
        ):
            mock_trade_repo_cls.return_value.create_paper_trade_atr.return_value = MagicMock(id=1)
            mock_opp_repo_cls.return_value.update_opportunity_status.return_value = None
            mock_funding_cls.return_value.scan.return_value = [
                MagicMock(
                    symbol="BTC-USDT-SWAP",
                    strategy_type=StrategyType.FUNDING,
                    direction=Direction.LONG,
                    raw_signals={"last_price": "100"},
                    detected_at=datetime.now(tz=UTC),
                    confidence=0.8,
                ),
            ]
            stats = loop.run_cycle(tier=1)

        assert stats.total_scanned == 1
        assert stats.candidates == 1
        assert stats.approved == 1
        assert stats.rejected == 0
        assert mock_session.commit.call_count == 2  # tier refresh + cycle
        mock_state.set_tier_scan.assert_called_once()

    def test_single_instrument_error_does_not_crash_cycle(self) -> None:
        mock_client = MagicMock()
        mock_client.get_tickers.return_value = [
            _swap_ticker("BTC-USDT-SWAP"),
            _swap_ticker("ETH-USDT-SWAP"),
        ]
        mock_client.get_funding_rates.side_effect = [
            [_funding_row("BTC-USDT-SWAP")],
            Exception("API error"),
        ]
        mock_client.get_candles.return_value = []

        mock_session = MagicMock()
        instruments = [
            _make_instrument("BTC-USDT-SWAP", tier=1),
            _make_instrument("ETH-USDT-SWAP", tier=1),
        ]
        instruments[1].id = 2

        mock_instrument_repo = MagicMock()
        mock_instrument_repo.get_instruments_by_tier.return_value = instruments

        mock_scorer = MagicMock()
        mock_scored = MagicMock()
        mock_scored.total_score = 70
        mock_scored.grade.value = "WATCH"
        mock_scored.opportunity_id = 1
        mock_scored.candidate.symbol = "BTC-USDT-SWAP"
        mock_scorer.score.return_value = mock_scored

        mock_risk = MagicMock()
        mock_decision = MagicMock()
        mock_decision.approved = True
        mock_risk.evaluate.return_value = mock_decision

        settings = _settings()
        loop = ScannerLoop(
            settings=settings,
            client=mock_client,
            session_factory=lambda: mock_session,
            state=MagicMock(),
        )

        with (
            patch("src.worker.scanner_loop.InstrumentRepository", return_value=mock_instrument_repo),
            patch("src.worker.scanner_loop.OpportunityScorer", return_value=mock_scorer),
            patch("src.worker.scanner_loop.RiskFilter", return_value=mock_risk),
            patch("src.worker.scanner_loop.StrategySettingsRepository", return_value=_mock_strategy_settings_repo()),
            patch("src.worker.scanner_loop.FundingStrategy") as mock_funding_cls,
        ):
            mock_funding_cls.return_value.scan.side_effect = [
                [MagicMock(
                    symbol="BTC-USDT-SWAP",
                    strategy_type=StrategyType.FUNDING,
                    direction=Direction.LONG,
                    raw_signals={"last_price": "100"},
                    detected_at=datetime.now(tz=UTC),
                    confidence=0.8,
                )],
                [],
            ]
            stats = loop.run_cycle(tier=1)

        assert stats.total_scanned == 2
        assert stats.errors >= 1
        assert mock_session.commit.call_count == 2

    def test_graceful_shutdown(self) -> None:
        mock_state = MagicMock()
        settings = _settings()
        scheduler = TierScheduler(settings=settings)

        loop = ScannerLoop(
            settings=settings,
            client=MagicMock(),
            session_factory=lambda: MagicMock(),
            scheduler=scheduler,
            state=mock_state,
        )

        def shutdown_after_delay() -> None:
            time.sleep(0.05)
            loop.request_shutdown()

        thread = threading.Thread(target=shutdown_after_delay, daemon=True)
        thread.start()

        with patch.object(loop, "run_cycle", return_value=MagicMock(
            tier=1, total_scanned=0, candidates=0, approved=0, rejected=0,
            duration_seconds=0.01, errors=0,
        )):
            loop.run_forever()

        assert not loop.running
        mock_state.mark_stopped.assert_called_once()
        thread.join(timeout=2)
