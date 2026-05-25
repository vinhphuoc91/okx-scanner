"""Paper trade lifecycle tracker with ATR-based SL/TP and M15 confirmation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.collector.rest_client import OKXRestClient
from src.collector.normalizer import normalize_ticker
from src.db.models import Opportunity, OpportunitySide, OpportunityStatus, PaperTradeStatus
from src.db.repositories.opportunity import OpportunityRepository
from src.db.repositories.paper_trade import PaperTradeRepository
from src.db.repositories.strategy_settings import StrategySettingsRepository
from src.schemas.market import NormalizedCandle, NormalizedTicker
from src.strategy.indicators import calc_atr
from src.strategy.momentum import _closes, calc_rsi
from src.utils.logger import get_logger
from src.worker.pending_confirmations import (
    MAX_PENDING,
    PendingConfirmation,
    PendingConfirmationStore,
)

log = get_logger(__name__)

MIN_CONFIRM_MINUTES = 15


def _parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class PaperTradeTracker:
    """Create, confirm, and monitor simulated trades."""

    def __init__(
        self,
        client: OKXRestClient | None = None,
        pending_store: PendingConfirmationStore | None = None,
    ) -> None:
        self._client = client
        self._pending = pending_store or PendingConfirmationStore()
        self._skip_confirm_this_cycle: set[int] = set()

    def begin_scan_cycle(self) -> None:
        """Reset per-cycle guards before a scanner tier pass."""
        self._skip_confirm_this_cycle.clear()

    def _resolve_atr(
        self,
        *,
        symbol: str,
        tier: int,
        candles_h1: list[NormalizedCandle] | None,
        strat_settings,
    ) -> float:
        """Return ATR in price units, or 0 when percent fallback should be used."""
        candle_count = len(candles_h1 or [])
        atr_value = calc_atr(candles_h1 or [], period=14)

        if atr_value is not None and atr_value > 0:
            log.info(
                "atr.calculated",
                symbol=symbol,
                atr=atr_value,
                candle_count=candle_count,
                timeframe="1H",
            )
            return atr_value

        if candle_count < 15:
            reason = "insufficient_candles"
        elif atr_value is not None and atr_value <= 0:
            reason = "zero_atr"
        else:
            reason = "atr_unavailable"

        tier_cfg = strat_settings.tier_params(tier or 3)
        log.warning(
            "atr.fallback",
            symbol=symbol,
            reason=reason,
            candle_count=candle_count,
            tier=tier or 3,
            sl_pct=tier_cfg["sl_pct"],
            tp_pct=tier_cfg["tp_pct"],
        )
        return 0.0

    def create_trade_from_opportunity(
        self,
        session: Session,
        *,
        opportunity_id: int,
        symbol: str,
        strategy: str,
        direction: str,
        tier: int,
        ticker: NormalizedTicker,
        candles_h1: list[NormalizedCandle] | None = None,
    ) -> None:
        """Open or queue a paper trade when an opportunity is approved."""
        log.info(
            "trade.create_attempt",
            opportunity_id=opportunity_id,
            symbol=symbol,
            strategy=strategy,
            direction=direction,
        )

        entry_price = ticker.last_price
        if entry_price <= 0:
            log.warning("paper_trade.skip_invalid_price", opportunity_id=opportunity_id, symbol=symbol)
            return

        settings_repo = StrategySettingsRepository(session)
        strat_settings = settings_repo.get_settings(strategy)
        if strat_settings is None:
            log.warning("paper_trade.unknown_strategy", strategy=strategy)
            return

        repo = PaperTradeRepository(session)
        global_cfg = settings_repo.get_global_config()

        atr_cfg = strat_settings.tier_atr_params(tier or 3)
        sl_mult = float(atr_cfg["sl_multiplier"])
        tp_mult = float(atr_cfg["tp_multiplier"])
        timeout_hours = int(atr_cfg["timeout_hours"])

        atr_value = self._resolve_atr(
            symbol=symbol,
            tier=tier or 3,
            candles_h1=candles_h1,
            strat_settings=strat_settings,
        )

        log.info(
            "trade.atr_calculated",
            symbol=symbol,
            strategy=strategy,
            atr=atr_value,
            sl_multiplier=sl_mult,
            tp_multiplier=tp_mult,
            pct_fallback=atr_value <= 0,
        )

        if strat_settings.requires_confirmation:
            if self._pending.get(opportunity_id) is not None:
                log.info(
                    "trade.skip_already_pending",
                    opportunity_id=opportunity_id,
                    symbol=symbol,
                    strategy=strategy,
                )
                return

            if self._pending.active_count() >= MAX_PENDING:
                log.info(
                    "trade.skip_max_pending",
                    opportunity_id=opportunity_id,
                    symbol=symbol,
                    strategy=strategy,
                    pending_count=self._pending.active_count(),
                    max_pending=MAX_PENDING,
                )
                return

            if self._pending.has_symbol_strategy(symbol, strategy):
                log.info(
                    "trade.skip_duplicate_pending",
                    opportunity_id=opportunity_id,
                    symbol=symbol,
                    strategy=strategy,
                )
                return

            if not repo.can_open_trade(
                symbol=symbol,
                strategy_type=strategy,
                direction=direction,
                strat_settings=strat_settings,
                queue_only=True,
            ):
                log.info(
                    "trade.skip_queue_blocked",
                    opportunity_id=opportunity_id,
                    symbol=symbol,
                    strategy=strategy,
                    reason="cooldown_or_duplicate_running",
                )
                return

            pending = PendingConfirmationStore.build(
                opportunity_id=opportunity_id,
                symbol=symbol,
                strategy=strategy,
                direction=direction,
                tier=tier or 3,
                signal_price=entry_price,
                atr_value=atr_value,
                sl_multiplier=sl_mult,
                tp_multiplier=tp_mult,
                timeout_hours=timeout_hours,
                confirmation_candles=strat_settings.confirmation_candles,
            )
            self._pending.save(pending)
            self._skip_confirm_this_cycle.add(opportunity_id)
            OpportunityRepository(session).update_opportunity_status(
                opportunity_id,
                OpportunityStatus.PENDING_CONFIRM,
            )
            log.info(
                "trade.pending_confirm",
                symbol=symbol,
                strategy=strategy,
                direction=direction,
                signal_price=str(entry_price),
                atr=atr_value,
                confirmation_candles=strat_settings.confirmation_candles,
            )
            return

        running_count = len(repo.get_running_trades())
        if running_count >= global_cfg.max_total_concurrent_trades:
            log.info(
                "paper_trade.skip_global_max_concurrent",
                symbol=symbol,
                strategy=strategy,
                running=running_count,
                max_allowed=global_cfg.max_total_concurrent_trades,
            )
            return

        if not repo.can_open_trade(
            symbol=symbol,
            strategy_type=strategy,
            direction=direction,
            strat_settings=strat_settings,
        ):
            log.info(
                "trade.skip_open_blocked",
                opportunity_id=opportunity_id,
                symbol=symbol,
                strategy=strategy,
                reason="max_concurrent_cooldown_or_duplicate",
            )
            return

        trade = repo.create_paper_trade_atr(
            opportunity_id=opportunity_id,
            symbol=symbol,
            strategy_type=strategy,
            direction=direction,
            entry_price=entry_price,
            tier=tier or 3,
            atr_value=atr_value,
            sl_multiplier=sl_mult,
            tp_multiplier=tp_mult,
            timeout_hours=timeout_hours,
            confirmation_required=False,
            signal_price=entry_price,
            confirmed_at=None,
            strat_settings=strat_settings,
        )
        if trade is not None:
            log.info(
                "trade.created",
                trade_id=trade.id,
                symbol=symbol,
                strategy=strategy,
                direction=direction,
                entry=str(entry_price),
                sl=str(trade.sl_price),
                tp=str(trade.tp_price),
                atr=atr_value,
                instant=True,
            )
            log.info(
                "trade.confirmed",
                symbol=symbol,
                strategy=strategy,
                entry=str(entry_price),
                sl=str(trade.sl_price),
                tp=str(trade.tp_price),
                atr=atr_value,
                instant=True,
            )

    def check_pending_confirmations(
        self,
        session: Session,
        ticker_map: dict[str, NormalizedTicker],
        candles_m15_map: dict[str, list[NormalizedCandle]],
    ) -> int:
        """Evaluate pending M15 confirmations; return count resolved."""
        pending_list, stale_ids = self._pending.list_all_with_stale()
        opp_repo = OpportunityRepository(session)
        now = datetime.now(tz=UTC)
        resolved = 0

        for opp_id in stale_ids:
            if opp_id in self._skip_confirm_this_cycle:
                continue
            opp_repo.update_opportunity_status(opp_id, OpportunityStatus.CONFIRM_FAILED)
            log.info(
                "trade.confirm_failed",
                opportunity_id=opp_id,
                reason="redis_ttl_expired",
            )
            resolved += 1

        if stale_ids:
            session.flush()

        resolved += self._reconcile_db_pending_orphans(session, {p.opportunity_id for p in pending_list})

        if not pending_list:
            return resolved

        repo = PaperTradeRepository(session)
        settings_repo = StrategySettingsRepository(session)
        global_cfg = settings_repo.get_global_config()

        for pending in pending_list:
            result, fail_reason = self._evaluate_pending(
                pending,
                candles_m15_map.get(pending.symbol, []),
                now,
            )
            if result == "wait":
                continue

            if result == "failed":
                if pending.opportunity_id in self._skip_confirm_this_cycle:
                    continue
                opp_repo.update_opportunity_status(
                    pending.opportunity_id,
                    OpportunityStatus.CONFIRM_FAILED,
                )
                self._pending.remove(pending.opportunity_id)
                log.info(
                    "trade.confirm_failed",
                    opportunity_id=pending.opportunity_id,
                    symbol=pending.symbol,
                    strategy=pending.strategy,
                    reason=fail_reason or "timeout",
                    confirmation_candles=pending.confirmation_candles,
                )
                resolved += 1
                continue

            ticker = ticker_map.get(pending.symbol)
            if ticker is None or ticker.last_price <= 0:
                continue

            strat_settings = settings_repo.get_settings(pending.strategy)
            if strat_settings is None:
                continue

            running_count = len(repo.get_running_trades())
            if running_count >= global_cfg.max_total_concurrent_trades:
                log.info(
                    "paper_trade.skip_global_max_concurrent",
                    symbol=pending.symbol,
                    strategy=pending.strategy,
                    running=running_count,
                    max_allowed=global_cfg.max_total_concurrent_trades,
                    context="pending_confirm",
                )
                continue

            if not repo.can_open_trade(
                symbol=pending.symbol,
                strategy_type=pending.strategy,
                direction=pending.direction,
                strat_settings=strat_settings,
            ):
                log.info(
                    "trade.skip_confirm_blocked",
                    symbol=pending.symbol,
                    strategy=pending.strategy,
                    reason="max_concurrent_cooldown_or_duplicate",
                )
                continue

            entry_price = ticker.last_price
            confirmed_at = now
            trade = repo.create_paper_trade_atr(
                opportunity_id=pending.opportunity_id,
                symbol=pending.symbol,
                strategy_type=pending.strategy,
                direction=pending.direction,
                entry_price=entry_price,
                tier=pending.tier,
                atr_value=pending.atr_value,
                sl_multiplier=pending.sl_multiplier,
                tp_multiplier=pending.tp_multiplier,
                timeout_hours=pending.timeout_hours,
                confirmation_required=True,
                signal_price=Decimal(pending.signal_price),
                confirmed_at=confirmed_at,
                strat_settings=strat_settings,
            )
            if trade is not None:
                opp_repo.update_opportunity_status(pending.opportunity_id, OpportunityStatus.APPROVED)
                self._pending.remove(pending.opportunity_id)
                wait_min = (confirmed_at - datetime.fromisoformat(pending.created_at)).total_seconds() / 60
                log.info(
                    "trade.created",
                    trade_id=trade.id,
                    symbol=pending.symbol,
                    strategy=pending.strategy,
                    direction=pending.direction,
                    entry=str(entry_price),
                    sl=str(trade.sl_price),
                    tp=str(trade.tp_price),
                    atr=pending.atr_value,
                    wait_minutes=round(wait_min, 1),
                )
                log.info(
                    "trade.confirmed",
                    symbol=pending.symbol,
                    strategy=pending.strategy,
                    entry=str(entry_price),
                    sl=str(trade.sl_price),
                    tp=str(trade.tp_price),
                    atr=pending.atr_value,
                    wait_minutes=round(wait_min, 1),
                )
                resolved += 1

        return resolved

    def _reconcile_db_pending_orphans(self, session: Session, active_ids: set[int]) -> int:
        """Mark stale DB PENDING_CONFIRM rows with no active Redis entry as CONFIRM_FAILED."""
        orphans = session.scalars(
            select(Opportunity).where(Opportunity.status == OpportunityStatus.PENDING_CONFIRM),
        ).all()
        if not orphans:
            return 0

        opp_repo = OpportunityRepository(session)
        now = datetime.now(tz=UTC)
        min_age = timedelta(minutes=MIN_CONFIRM_MINUTES)
        resolved = 0
        for opp in orphans:
            if opp.id in active_ids or opp.id in self._skip_confirm_this_cycle:
                continue
            updated_at = opp.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)
            if now - updated_at < min_age:
                continue
            opp_repo.update_opportunity_status(opp.id, OpportunityStatus.CONFIRM_FAILED)
            log.info(
                "trade.confirm_failed",
                opportunity_id=opp.id,
                symbol=None,
                strategy=opp.strategy,
                reason="orphan_not_in_redis",
            )
            resolved += 1
        return resolved

    def _evaluate_pending(
        self,
        pending: PendingConfirmation,
        candles_m15: list[NormalizedCandle],
        now: datetime,
    ) -> tuple[str, str | None]:
        """Return ('confirmed'|'failed'|'wait', optional fail reason)."""
        created = _parse_utc(pending.created_at)
        elapsed = now - created
        max_wait = timedelta(minutes=max(MIN_CONFIRM_MINUTES, 15 * pending.confirmation_candles))

        if len(candles_m15) < 21:
            if elapsed > max_wait:
                elapsed_min = round(elapsed.total_seconds() / 60, 1)
                return "failed", f"timeout_insufficient_candles_{elapsed_min}m"
            return "wait", None

        sorted_m15 = sorted(candles_m15, key=lambda c: c.open_time)
        latest = sorted_m15[-1]
        closes = _closes(sorted_m15)
        rsi = calc_rsi(closes, 14)
        if rsi is None:
            if elapsed > max_wait:
                elapsed_min = round(elapsed.total_seconds() / 60, 1)
                return "failed", f"timeout_no_rsi_{elapsed_min}m"
            return "wait", None

        avg_vol = sum(c.volume for c in sorted_m15[-21:-1]) / Decimal("20")
        vol_ok = avg_vol > 0 and latest.volume >= avg_vol
        signal = Decimal(pending.signal_price)
        is_long = pending.direction.upper() == "LONG"

        if is_long:
            price_ok = latest.close > signal
            rsi_ok = rsi > Decimal("50")
        else:
            price_ok = latest.close < signal
            rsi_ok = rsi < Decimal("50")

        if price_ok and rsi_ok and vol_ok:
            return "confirmed", None

        if elapsed > max_wait:
            elapsed_min = round(elapsed.total_seconds() / 60, 1)
            return "failed", f"timeout_criteria_not_met_{elapsed_min}m"
        return "wait", None

    def check_running_trades(
        self,
        session: Session,
        ticker_map: dict[str, NormalizedTicker],
        *,
        client: OKXRestClient | None = None,
    ) -> int:
        """Evaluate open trades against live prices; return number closed."""
        repo = PaperTradeRepository(session)
        running = repo.get_running_trades()
        if not running:
            return 0

        prices = self._build_price_map(running, ticker_map, client or self._client)
        now = datetime.now(tz=UTC)
        closed_count = 0

        for trade in running:
            price = prices.get(trade.symbol)
            if price is None:
                continue

            status = self._evaluate_trade(trade, price, now)
            if status is None:
                continue

            closed = repo.close_trade(trade.id, price, status)
            if closed is not None:
                duration = (now - trade.entry_at).total_seconds() / 60
                log.info(
                    "trade.closed",
                    symbol=trade.symbol,
                    strategy=trade.strategy_type,
                    status=status.value,
                    pnl_pct=float(closed.pnl_pct or 0),
                    duration_min=round(duration, 1),
                    atr_used=float(trade.atr_value) if trade.atr_value else None,
                )
                closed_count += 1

        return closed_count

    def _build_price_map(
        self,
        running: list,
        ticker_map: dict[str, NormalizedTicker],
        client: OKXRestClient | None,
    ) -> dict[str, Decimal]:
        prices: dict[str, Decimal] = {}
        missing: set[str] = set()

        for trade in running:
            ticker = ticker_map.get(trade.symbol)
            if ticker is not None:
                prices[trade.symbol] = ticker.last_price
            else:
                missing.add(trade.symbol)

        if missing and client is not None:
            for raw in client.get_tickers("SWAP"):
                try:
                    ticker = normalize_ticker(raw)
                    if ticker.inst_id in missing:
                        prices[ticker.inst_id] = ticker.last_price
                except ValueError:
                    continue

        return prices

    @staticmethod
    def _evaluate_trade(trade, current_price: Decimal, now: datetime) -> PaperTradeStatus | None:
        is_long = trade.direction == OpportunitySide.LONG
        timeout_at = trade.entry_at + timedelta(hours=trade.timeout_hours)

        if is_long:
            if current_price >= trade.tp_price:
                return PaperTradeStatus.WIN
            if current_price <= trade.sl_price:
                return PaperTradeStatus.LOSS
        else:
            if current_price <= trade.tp_price:
                return PaperTradeStatus.WIN
            if current_price >= trade.sl_price:
                return PaperTradeStatus.LOSS

        if now >= timeout_at:
            return PaperTradeStatus.EXPIRED

        return None

    def get_pending_items(self) -> list[dict]:
        return [self._pending.pending_to_dict(p) for p in self._pending.list_all()]
