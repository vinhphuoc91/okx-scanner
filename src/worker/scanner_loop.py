"""Main scanner worker loop — full M1→M5 pipeline per tier."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session, sessionmaker

from config.settings import Settings, get_settings
from src.collector.normalizer import (
    calc_oi_change_pct,
    normalize_candle,
    normalize_funding_rate,
    normalize_ticker,
)
from src.collector.rest_client import OKXRestClient
from src.db.repositories.instrument import InstrumentRepository
from src.db.repositories.strategy_settings import StrategySettingsRepository
from src.db.session import get_session_factory
from src.filter.market_filter import MarketFilter
from src.risk.risk_filter import RiskFilter
from src.scoring.scorer import OpportunityScorer
from src.strategy.base import BenchmarkSnapshot, MarketContext
from src.strategy.breakout import BreakoutStrategy
from src.strategy.correlation_divergence import CorrelationDivergenceStrategy
from src.strategy.funding import FundingStrategy
from src.strategy.liquidation_zone import LiquidationZoneStrategy
from src.strategy.momentum import MomentumStrategy
from src.strategy.stat_arb import StatArbitrageStrategy
from src.strategy.helpers import (
    btc_uptrend_h1,
    calc_basis_pct,
    calc_price_change_pct,
    sort_candles,
    swap_to_spot_id,
)
from src.strategy.trend_pullback import TrendPullbackStrategy
from src.strategy.volume_anomaly import VolumeAnomalyStrategy
from src.utils.logger import get_logger
from src.worker.scanner_state import ScannerState
from src.worker.scheduler import TierScheduler
from src.worker.trade_tracker import PaperTradeTracker

log = get_logger(__name__)

_IDLE_SLEEP_SECONDS = 1.0


@dataclass
class CycleStats:
    """Metrics for one tier scan cycle."""

    tier: int
    total_scanned: int = 0
    candidates: int = 0
    approved: int = 0
    rejected: int = 0
    duration_seconds: float = 0.0
    errors: int = 0


@dataclass
class ScannerTotals:
    """Cumulative stats across all completed cycles."""

    total_scanned: int = 0
    candidates: int = 0
    approved: int = 0
    rejected: int = 0
    cycles: int = 0
    errors: int = field(default=0)


class ScannerLoop:
    """Orchestrate tier-scheduled market scans through the full pipeline."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: OKXRestClient | None = None,
        session_factory: Callable[[], Session] | None = None,
        scheduler: TierScheduler | None = None,
        state: ScannerState | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or OKXRestClient()
        self._owns_client = client is None
        self._session_factory = session_factory or get_session_factory()
        self._scheduler = scheduler or TierScheduler(settings=self._settings)
        self._state = state or ScannerState()
        self._trade_tracker = PaperTradeTracker(client=self._client)
        self._running = True
        self._totals = ScannerTotals()

    @property
    def totals(self) -> ScannerTotals:
        """Return cumulative scan statistics."""
        return self._totals

    @property
    def running(self) -> bool:
        return self._running

    def request_shutdown(self) -> None:
        """Signal graceful shutdown after the current cycle completes."""
        self._running = False
        log.info("scanner.shutdown_requested")

    def run_forever(self) -> None:
        """Main worker loop until :meth:`request_shutdown` is called."""
        started_at = datetime.now(tz=timezone.utc)
        self._state.mark_running(started_at)
        log.info("scanner.start", env=self._settings.app_env.value)

        try:
            while True:
                self._state.heartbeat()
                if not self._running:
                    break

                due = self._scheduler.get_due_tiers()
                if not due:
                    time.sleep(_IDLE_SLEEP_SECONDS)
                    continue

                for tier in sorted(due):
                    stats = self.run_cycle(tier)
                    self._scheduler.mark_scanned(tier)
                    self._accumulate(stats)
                    if not self._running:
                        break
        finally:
            self._state.mark_stopped()
            if self._owns_client:
                self._client.close()
            log.info(
                "scanner.stop",
                cycles=self._totals.cycles,
                total_scanned=self._totals.total_scanned,
                candidates=self._totals.candidates,
                approved=self._totals.approved,
                rejected=self._totals.rejected,
            )

    def run_cycle(self, tier: int) -> CycleStats:
        """Execute one full scan cycle for *tier*."""
        started = time.perf_counter()
        stats = CycleStats(tier=tier)
        session = self._session_factory()

        try:
            if tier == 1:
                self._refresh_tiers(session)
                session.commit()

            instruments = InstrumentRepository(session).get_instruments_by_tier(tier)
            if not instruments:
                log.warning("scanner.cycle.empty_tier", tier=tier)
                stats.duration_seconds = time.perf_counter() - started
                return stats

            inst_ids = {inst.inst_id for inst in instruments}
            ticker_map = self._fetch_ticker_map(inst_ids)
            market_filter = MarketFilter(settings=self._settings)
            tier_tickers = [ticker_map[i] for i in inst_ids if i in ticker_map]
            filter_result = market_filter.filter_instruments(tier_tickers)
            passed_ids = {item.inst_id for item in filter_result.passed}

            funding_strategy = FundingStrategy(settings=self._settings)
            momentum_strategy = MomentumStrategy(settings=self._settings)
            breakout_strategy = BreakoutStrategy(settings=self._settings)
            volume_anomaly_strategy = VolumeAnomalyStrategy(settings=self._settings)
            trend_pullback_strategy = TrendPullbackStrategy(settings=self._settings)
            correlation_strategy = CorrelationDivergenceStrategy(settings=self._settings)
            liquidation_strategy = LiquidationZoneStrategy(settings=self._settings)
            stat_arb_strategy = StatArbitrageStrategy(settings=self._settings)
            strategy_map = {
                "FUNDING": funding_strategy,
                "MOMENTUM": momentum_strategy,
                "BREAKOUT": breakout_strategy,
                "VOLUME_ANOMALY": volume_anomaly_strategy,
                "TREND_PULLBACK": trend_pullback_strategy,
                "CORRELATION_DIVERGENCE": correlation_strategy,
                "LIQUIDATION_ZONE": liquidation_strategy,
                "STAT_ARBITRAGE": stat_arb_strategy,
            }

            settings_repo = StrategySettingsRepository(session)
            strat_settings_map = settings_repo.get_all_settings()
            global_cfg = settings_repo.get_global_config()
            strategies = [
                strategy_map[key]
                for key in strategy_map
                if key in strat_settings_map and strat_settings_map[key].is_enabled
            ]
            log.info(
                "scanner.strategies_enabled",
                tier=tier,
                strategies=[s.name for s in strategies],
            )
            scorer = OpportunityScorer(
                settings=self._settings,
                session=session,
                persist=True,
            )
            risk_filter = RiskFilter(
                settings=self._settings,
                session=session,
                persist=True,
            )

            closed_trades = self._trade_tracker.check_running_trades(
                session, ticker_map, client=self._client,
            )
            if closed_trades:
                log.info("paper_trade.cycle_closed", count=closed_trades)

            self._trade_tracker.begin_scan_cycle()

            benchmark = self._build_benchmark()
            spot_ticker_map = self._fetch_spot_ticker_map(inst_ids)
            instrument_tiers = {inst.inst_id: inst.tier or 3 for inst in instruments}

            candles_m15_map: dict[str, list] = {}
            for pending in self._trade_tracker.get_pending_items():
                sym = pending["symbol"]
                if sym not in candles_m15_map:
                    candles_m15_map[sym] = self._fetch_candles(sym, "15m")

            for instrument in instruments:
                inst_id = instrument.inst_id
                stats.total_scanned += 1
                try:
                    if inst_id not in passed_ids:
                        continue
                    ticker = ticker_map.get(inst_id)
                    if ticker is None:
                        continue

                    ctx = self._build_context(
                        inst_id,
                        ticker,
                        tier=instrument_tiers.get(inst_id, 3),
                        benchmark=benchmark,
                        spot_ticker=spot_ticker_map.get(swap_to_spot_id(inst_id) or ""),
                    )
                    candles_m15_map[inst_id] = ctx.candles_m15
                    candidates: list = []
                    for strategy in strategies:
                        found = strategy.scan(ctx)
                        if found:
                            log.debug(
                                "scanner.strategy.candidates",
                                inst_id=inst_id,
                                strategy=strategy.name,
                                count=len(found),
                            )
                        candidates.extend(found)

                    for candidate in candidates:
                        stats.candidates += 1
                        scored = scorer.score(candidate, ctx)
                        if scored.opportunity_id is None:
                            log.warning(
                                "scanner.candidate.persist_failed",
                                inst_id=inst_id,
                                symbol=candidate.symbol,
                            )
                            stats.errors += 1
                            continue
                        session.flush()
                        strategy_key = scored.candidate.strategy_type.value
                        strat_cfg = strat_settings_map.get(strategy_key)
                        min_score = (
                            strat_cfg.min_score
                            if strat_cfg is not None
                            else global_cfg.alert_min_score
                        )
                        decision = risk_filter.evaluate(scored, ctx, min_score=min_score)
                        if decision.approved:
                            stats.approved += 1
                            log.info(
                                "scanner.trade_tracker.invoke",
                                opportunity_id=scored.opportunity_id,
                                symbol=inst_id,
                                strategy=scored.candidate.strategy_type.value,
                                direction=scored.candidate.direction.value,
                            )
                            self._trade_tracker.create_trade_from_opportunity(
                                session,
                                opportunity_id=scored.opportunity_id,
                                symbol=inst_id,
                                strategy=scored.candidate.strategy_type.value,
                                direction=scored.candidate.direction.value,
                                tier=instrument.tier or 3,
                                ticker=ticker,
                                candles_h1=ctx.candles_h1,
                            )
                        else:
                            stats.rejected += 1
                            score = scored.total_score
                            if 60 <= score <= 64:
                                log.info(
                                    "scanner.trade_skipped",
                                    symbol=inst_id,
                                    strategy=strategy_key,
                                    direction=scored.candidate.direction.value,
                                    score=score,
                                    min_score=min_score,
                                    grade=scored.grade.value,
                                    rejection_codes=[
                                        code.value for code in decision.rejection_codes
                                    ],
                                    checks=decision.raw_checks,
                                )
                except Exception:
                    stats.errors += 1
                    log.exception("scanner.instrument.error", inst_id=inst_id, tier=tier)

            confirmed = self._trade_tracker.check_pending_confirmations(
                session, ticker_map, candles_m15_map,
            )
            if confirmed:
                log.info("trade.pending_resolved", count=confirmed)

            session.commit()
            scanned_at = datetime.now(tz=timezone.utc)
            self._state.set_tier_scan(tier, scanned_at)
            stats.duration_seconds = time.perf_counter() - started

            log.info(
                "scanner.cycle.complete",
                tier=tier,
                scanned=stats.total_scanned,
                candidates=stats.candidates,
                approved=stats.approved,
                rejected=stats.rejected,
                errors=stats.errors,
                duration_ms=round(stats.duration_seconds * 1000, 2),
            )
            return stats
        except Exception:
            session.rollback()
            log.exception("scanner.cycle.failed", tier=tier)
            raise
        finally:
            session.close()

    def _accumulate(self, stats: CycleStats) -> None:
        self._totals.cycles += 1
        self._totals.total_scanned += stats.total_scanned
        self._totals.candidates += stats.candidates
        self._totals.approved += stats.approved
        self._totals.rejected += stats.rejected
        self._totals.errors += stats.errors
        self._state.update_cycle_stats(
            {
                "total_scanned": stats.total_scanned,
                "candidates": stats.candidates,
                "approved": stats.approved,
                "rejected": stats.rejected,
                "errors": stats.errors,
            },
        )

    def _refresh_tiers(self, session: Session) -> None:
        """Recompute tier assignments from live SWAP tickers (tier-1 cycles only)."""
        raw_tickers = self._client.get_tickers("SWAP")
        tickers = []
        for raw in raw_tickers:
            try:
                tickers.append(normalize_ticker(raw))
            except ValueError:
                log.warning("scanner.ticker.normalize_failed", raw_inst=raw.get("instId"))

        market_filter = MarketFilter(settings=self._settings)
        filtered = market_filter.filter_instruments(tickers)
        tiered = market_filter.assign_tiers(filtered.passed)
        repo = InstrumentRepository(session)

        updated = 0
        for item in (*tiered.tier1, *tiered.tier2, *tiered.tier3):
            row = repo.update_instrument_tier(
                item.inst_id,
                item.tier or 3,
                scan_interval_seconds=item.scan_interval_seconds,
            )
            if row is not None:
                updated += 1

        log.info(
            "scanner.tiers_refreshed",
            passed=len(filtered.passed),
            tier1=len(tiered.tier1),
            tier2=len(tiered.tier2),
            tier3=len(tiered.tier3),
            updated=updated,
        )

    def _fetch_ticker_map(self, inst_ids: set[str]) -> dict:
        """Build ``inst_id → NormalizedTicker`` for the requested set."""
        ticker_map: dict = {}
        for raw in self._client.get_tickers("SWAP"):
            try:
                ticker = normalize_ticker(raw)
                if ticker.inst_id in inst_ids:
                    ticker_map[ticker.inst_id] = ticker
            except ValueError:
                continue
        return ticker_map

    def _build_benchmark(self) -> BenchmarkSnapshot | None:
        """Fetch BTC/ETH H1 candles and compute benchmark snapshot."""
        try:
            btc_h1 = self._fetch_candles("BTC-USDT-SWAP", "1H")
            eth_h1 = self._fetch_candles("ETH-USDT-SWAP", "1H")
            if len(btc_h1) < 25:
                log.warning("scanner.benchmark.insufficient_btc_candles")
                return None

            btc_c1 = calc_price_change_pct(btc_h1, 1)
            btc_c4 = calc_price_change_pct(btc_h1, 4)
            btc_c24 = calc_price_change_pct(btc_h1, 24)
            eth_c1 = calc_price_change_pct(eth_h1, 1) if eth_h1 else None
            eth_c4 = calc_price_change_pct(eth_h1, 4) if eth_h1 else None
            eth_c24 = calc_price_change_pct(eth_h1, 24) if eth_h1 else None
            trend_up = btc_uptrend_h1(btc_h1)

            btc_sorted = sort_candles(btc_h1)
            eth_sorted = sort_candles(eth_h1) if eth_h1 else []

            return BenchmarkSnapshot(
                btc_change_1h=btc_c1 or 0.0,
                btc_change_4h=btc_c4 or 0.0,
                btc_change_24h=btc_c24 or 0.0,
                eth_change_1h=eth_c1 or 0.0,
                eth_change_4h=eth_c4 or 0.0,
                eth_change_24h=eth_c24 or 0.0,
                btc_trend_up=trend_up if trend_up is not None else False,
                btc_price=str(btc_sorted[-1].close),
                eth_price=str(eth_sorted[-1].close) if eth_sorted else "0",
            )
        except Exception:
            log.exception("scanner.benchmark.failed")
            return None

    def _fetch_spot_ticker_map(self, swap_inst_ids: set[str]) -> dict:
        """Map spot inst_id → NormalizedTicker for swaps with a spot pair."""
        spot_ids = {
            sid for sid in (swap_to_spot_id(i) for i in swap_inst_ids) if sid
        }
        if not spot_ids:
            return {}

        spot_map: dict = {}
        for raw in self._client.get_tickers("SPOT"):
            try:
                ticker = normalize_ticker(raw)
                if ticker.inst_id in spot_ids:
                    spot_map[ticker.inst_id] = ticker
            except ValueError:
                continue
        return spot_map

    def _build_context(
        self,
        inst_id: str,
        ticker,
        *,
        tier: int = 3,
        benchmark: BenchmarkSnapshot | None = None,
        spot_ticker=None,
    ) -> MarketContext:
        """Assemble :class:`MarketContext` with ticker, funding, candles, OI, spot."""
        funding = None
        if inst_id.endswith("-SWAP"):
            funding_rows = self._client.get_funding_rates(inst_id)
            if funding_rows:
                try:
                    funding = normalize_funding_rate(funding_rows[0])
                except ValueError:
                    log.warning("scanner.funding.normalize_failed", inst_id=inst_id)

        candles_m15 = self._fetch_candles(inst_id, "15m")
        candles_h1 = self._fetch_candles(inst_id, "1H")

        oi_value = None
        oi_change = None
        if inst_id.endswith("-SWAP"):
            oi_rows = self._client.get_open_interest(inst_id)
            if oi_rows and oi_rows[0].get("oi") is not None:
                try:
                    from decimal import Decimal
                    oi_value = Decimal(str(oi_rows[0]["oi"]))
                except Exception:
                    oi_value = None
            history = self._client.get_open_interest_history(inst_id, period="4H")
            oi_change = calc_oi_change_pct(history, lookback=1)

        basis_history: list[float] = []
        if spot_ticker is not None and ticker is not None:
            spot_id = spot_ticker.inst_id
            spot_m15 = self._fetch_candles(spot_id, "15m")
            perp_sorted = sort_candles(candles_m15)
            spot_sorted = sort_candles(spot_m15)
            periods = min(
                self._settings.stat_arb_basis_trend_periods,
                len(perp_sorted),
                len(spot_sorted),
            )
            for i in range(periods):
                idx = -(periods - i)
                basis = calc_basis_pct(spot_sorted[idx].close, perp_sorted[idx].close)
                if basis is not None:
                    basis_history.append(basis)

        return MarketContext(
            symbol=inst_id,
            ticker=ticker,
            funding_rate=funding,
            candles_m15=candles_m15,
            candles_h1=candles_h1,
            tier=tier,
            spot_ticker=spot_ticker,
            open_interest=oi_value,
            open_interest_change_4h_pct=oi_change,
            benchmark=benchmark,
            basis_history_pct=basis_history,
        )

    def _fetch_candles(self, inst_id: str, timeframe: str) -> list:
        """Fetch normalized candles for *inst_id*."""
        candles = []
        for raw in self._client.get_candles(inst_id, timeframe, limit=100):
            try:
                candles.append(normalize_candle(raw, inst_id, timeframe))
            except ValueError:
                pass
        return candles
