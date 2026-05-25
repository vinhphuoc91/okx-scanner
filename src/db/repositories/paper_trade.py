"""Paper trade repository — simulated trade tracking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import (
    Instrument,
    Opportunity,
    OpportunityScore,
    OpportunitySide,
    OpportunityStatus,
    PaperTrade,
    PaperTradeStatus,
)
from src.strategy.indicators import compute_atr_prices
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.db.models import StrategySettings

log = get_logger(__name__)

TIER_CONFIG: dict[int, dict[str, float | int]] = {
    1: {"sl_pct": 1.5, "tp_pct": 3.0, "timeout_hours": 8},
    2: {"sl_pct": 2.0, "tp_pct": 4.0, "timeout_hours": 12},
    3: {"sl_pct": 2.5, "tp_pct": 5.0, "timeout_hours": 24},
}


def tier_config(tier: int, strat_settings: StrategySettings | None = None) -> dict[str, float | int]:
    """Return SL/TP/timeout config for *tier* (defaults to tier 3)."""
    if strat_settings is not None:
        return strat_settings.tier_params(tier)
    return TIER_CONFIG.get(tier, TIER_CONFIG[3])


def compute_tp_sl_prices(
    entry_price: Decimal,
    direction: OpportunitySide | str,
    tp_pct: Decimal,
    sl_pct: Decimal,
) -> tuple[Decimal, Decimal]:
    """Calculate take-profit and stop-loss prices."""
    side = direction if isinstance(direction, OpportunitySide) else OpportunitySide(direction)
    tp_factor = tp_pct / Decimal("100")
    sl_factor = sl_pct / Decimal("100")
    if side == OpportunitySide.LONG:
        return entry_price * (Decimal("1") + tp_factor), entry_price * (Decimal("1") - sl_factor)
    return entry_price * (Decimal("1") - tp_factor), entry_price * (Decimal("1") + sl_factor)


def compute_pnl_pct(
    entry_price: Decimal,
    close_price: Decimal,
    direction: OpportunitySide | str,
) -> Decimal:
    """Return signed P&L percentage."""
    side = direction if isinstance(direction, OpportunitySide) else OpportunitySide(direction)
    if entry_price <= 0:
        return Decimal("0")
    change = (close_price - entry_price) / entry_price * Decimal("100")
    if side == OpportunitySide.SHORT:
        change = -change
    return change.quantize(Decimal("0.0001"))


class PaperTradeRepository:
    """CRUD helpers for :class:`~src.db.models.PaperTrade`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def can_open_trade(
        self,
        *,
        symbol: str,
        strategy_type: str,
        direction: str,
        strat_settings: StrategySettings,
        queue_only: bool = False,
    ) -> bool:
        """Check max concurrent and cooldown before opening a trade.

        When *queue_only* is True (M15 confirmation queue), skip per-strategy
        max-concurrent — the slot is not consumed until the trade opens.
        """
        strategy_key = strategy_type.upper()
        side = OpportunitySide(direction.upper())

        if not queue_only:
            running_same_strategy = self._session.scalar(
                select(func.count())
                .select_from(PaperTrade)
                .where(
                    PaperTrade.strategy_type == strategy_key,
                    PaperTrade.status == PaperTradeStatus.RUNNING,
                ),
            )
            if running_same_strategy is not None and running_same_strategy >= strat_settings.max_concurrent:
                log.info(
                    "paper_trade.skip_strategy_max_concurrent",
                    symbol=symbol,
                    strategy=strategy_key,
                    running=running_same_strategy,
                    max_allowed=strat_settings.max_concurrent,
                )
                return False

        last_trade = self._session.scalar(
            select(PaperTrade)
            .where(
                PaperTrade.symbol == symbol,
                PaperTrade.strategy_type == strategy_key,
                PaperTrade.direction == side,
            )
            .order_by(PaperTrade.entry_at.desc())
            .limit(1),
        )
        if last_trade is not None:
            cooldown = timedelta(hours=float(strat_settings.cooldown_hours))
            elapsed = datetime.now(tz=timezone.utc) - last_trade.entry_at
            if elapsed < cooldown:
                log.info(
                    "paper_trade.skip_cooldown",
                    symbol=symbol,
                    strategy=strategy_key,
                    direction=direction,
                    cooldown_hours=float(strat_settings.cooldown_hours),
                    elapsed_minutes=round(elapsed.total_seconds() / 60, 1),
                )
                return False

        running = self._session.scalar(
            select(PaperTrade).where(
                PaperTrade.symbol == symbol,
                PaperTrade.strategy_type == strategy_key,
                PaperTrade.direction == side,
                PaperTrade.status == PaperTradeStatus.RUNNING,
            ),
        )
        if running is not None:
            log.info(
                "paper_trade.skip_duplicate_running",
                symbol=symbol,
                strategy=strategy_key,
                direction=direction,
                existing_trade_id=running.id,
            )
            return False

        return True

    def create_paper_trade(
        self,
        *,
        opportunity_id: int,
        symbol: str,
        strategy_type: str,
        direction: str,
        entry_price: Decimal,
        tier: int,
        entry_at: datetime | None = None,
        strat_settings: StrategySettings | None = None,
    ) -> PaperTrade | None:
        """Open a paper trade for an approved opportunity."""
        side = OpportunitySide(direction.upper())

        existing_opp = self._session.scalar(
            select(PaperTrade).where(PaperTrade.opportunity_id == opportunity_id),
        )
        if existing_opp is not None:
            log.debug(
                "paper_trade.already_exists",
                opportunity_id=opportunity_id,
                trade_id=existing_opp.id,
            )
            return existing_opp

        cfg = tier_config(tier, strat_settings)
        tp_pct = Decimal(str(cfg["tp_pct"]))
        sl_pct = Decimal(str(cfg["sl_pct"]))
        tp_price, sl_price = compute_tp_sl_prices(entry_price, direction, tp_pct, sl_pct)
        now = entry_at or datetime.now(tz=timezone.utc)

        row = PaperTrade(
            opportunity_id=opportunity_id,
            symbol=symbol,
            strategy_type=strategy_type.upper(),
            direction=side,
            entry_price=entry_price,
            tp_price=tp_price,
            sl_price=sl_price,
            tp_pct=tp_pct,
            sl_pct=sl_pct,
            timeout_hours=int(cfg["timeout_hours"]),
            status=PaperTradeStatus.RUNNING,
            entry_at=now,
            tier=tier,
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        log.info(
            "paper_trade.created",
            trade_id=row.id,
            symbol=symbol,
            strategy=strategy_type,
            direction=direction,
            tier=tier,
            entry_price=str(entry_price),
            tp_price=str(tp_price),
            sl_price=str(sl_price),
        )
        return row

    def create_paper_trade_atr(
        self,
        *,
        opportunity_id: int,
        symbol: str,
        strategy_type: str,
        direction: str,
        entry_price: Decimal,
        tier: int,
        atr_value: float,
        sl_multiplier: float,
        tp_multiplier: float,
        timeout_hours: int,
        confirmation_required: bool,
        signal_price: Decimal | None = None,
        confirmed_at: datetime | None = None,
        entry_at: datetime | None = None,
        strat_settings: StrategySettings | None = None,
    ) -> PaperTrade | None:
        """Open a paper trade using ATR-based or percent-fallback SL/TP."""
        side = OpportunitySide(direction.upper())

        existing_opp = self._session.scalar(
            select(PaperTrade).where(PaperTrade.opportunity_id == opportunity_id),
        )
        if existing_opp is not None:
            return existing_opp

        if atr_value is None or atr_value <= 0:
            cfg = tier_config(tier, strat_settings)
            tp_price, sl_price = compute_tp_sl_prices(
                entry_price,
                side,
                Decimal(str(cfg["tp_pct"])),
                Decimal(str(cfg["sl_pct"])),
            )
            tp_pct = Decimal(str(cfg["tp_pct"]))
            sl_pct = Decimal(str(cfg["sl_pct"]))
            stored_atr: float | None = None
        else:
            tp_price, sl_price, tp_pct, sl_pct = compute_atr_prices(
                entry_price, direction, atr_value, sl_multiplier, tp_multiplier,
            )
            stored_atr = atr_value

        now = entry_at or datetime.now(tz=timezone.utc)

        row = PaperTrade(
            opportunity_id=opportunity_id,
            symbol=symbol,
            strategy_type=strategy_type.upper(),
            direction=side,
            entry_price=entry_price,
            tp_price=tp_price,
            sl_price=sl_price,
            tp_pct=tp_pct,
            sl_pct=sl_pct,
            timeout_hours=timeout_hours,
            status=PaperTradeStatus.RUNNING,
            entry_at=now,
            tier=tier,
            atr_value=Decimal(str(stored_atr)) if stored_atr is not None else None,
            sl_multiplier=Decimal(str(sl_multiplier)),
            tp_multiplier=Decimal(str(tp_multiplier)),
            signal_price=signal_price,
            confirmed_at=confirmed_at,
            confirmation_required=confirmation_required,
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        log.info(
            "paper_trade.created_atr",
            trade_id=row.id,
            symbol=symbol,
            strategy=strategy_type,
            atr=stored_atr,
            tp_price=str(tp_price),
            sl_price=str(sl_price),
            pct_fallback=stored_atr is None,
        )
        return row

    def get_running_trades(self) -> list[PaperTrade]:
        """Return all open paper trades."""
        stmt = (
            select(PaperTrade)
            .where(PaperTrade.status == PaperTradeStatus.RUNNING)
            .order_by(PaperTrade.entry_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    def close_trade(
        self,
        trade_id: int,
        close_price: Decimal,
        status: PaperTradeStatus | str,
    ) -> PaperTrade | None:
        """Close a paper trade and record P&L."""
        row = self._session.get(PaperTrade, trade_id)
        if row is None or row.status != PaperTradeStatus.RUNNING:
            return None

        resolved = (
            status if isinstance(status, PaperTradeStatus) else PaperTradeStatus(status)
        )
        now = datetime.now(tz=timezone.utc)
        pnl = compute_pnl_pct(row.entry_price, close_price, row.direction)

        row.close_price = close_price
        row.closed_at = now
        row.status = resolved
        row.pnl_pct = pnl

        log.info(
            "paper_trade.closed",
            trade_id=trade_id,
            symbol=row.symbol,
            status=resolved.value,
            pnl_pct=float(pnl),
            close_price=str(close_price),
        )
        return row

    def get_trades(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
        strategy: str | None = None,
        tier: int | None = None,
        direction: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return paper trades with optional filters (deduplicated)."""
        latest_sq = (
            select(
                PaperTrade.symbol,
                PaperTrade.strategy_type,
                PaperTrade.direction,
                func.max(PaperTrade.id).label("latest_id"),
            )
            .group_by(PaperTrade.symbol, PaperTrade.strategy_type, PaperTrade.direction)
            .subquery()
        )

        stmt = (
            select(PaperTrade)
            .join(latest_sq, PaperTrade.id == latest_sq.c.latest_id)
            .order_by(PaperTrade.entry_at.desc())
            .limit(limit)
        )

        if status:
            stmt = stmt.where(
                PaperTrade.status == PaperTradeStatus(status.upper()),
            )
        if strategy:
            stmt = stmt.where(PaperTrade.strategy_type == strategy.upper())
        if tier is not None:
            stmt = stmt.where(PaperTrade.tier == tier)
        if direction:
            stmt = stmt.where(PaperTrade.direction == OpportunitySide(direction.upper()))
        if date_from is not None:
            stmt = stmt.where(PaperTrade.entry_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(PaperTrade.entry_at <= date_to)

        rows = self._session.scalars(stmt).all()
        scores = self._load_latest_scores([row.opportunity_id for row in rows])
        return [self._to_dict(row, scores.get(row.opportunity_id)) for row in rows]

    def _load_latest_scores(
        self,
        opportunity_ids: list[int],
    ) -> dict[int, OpportunityScore]:
        """Return the latest score row per opportunity id."""
        if not opportunity_ids:
            return {}

        latest_sq = (
            select(
                OpportunityScore.opportunity_id,
                func.max(OpportunityScore.scored_at).label("max_scored_at"),
            )
            .where(OpportunityScore.opportunity_id.in_(opportunity_ids))
            .group_by(OpportunityScore.opportunity_id)
            .subquery()
        )
        stmt = (
            select(OpportunityScore)
            .join(
                latest_sq,
                (OpportunityScore.opportunity_id == latest_sq.c.opportunity_id)
                & (OpportunityScore.scored_at == latest_sq.c.max_scored_at),
            )
        )
        return {score.opportunity_id: score for score in self._session.scalars(stmt).all()}

    def get_confirm_failed(
        self,
        *,
        limit: int = 50,
        strategy: str | None = None,
        tier: int | None = None,
        direction: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return opportunities that failed M15 confirmation as alert-shaped rows."""
        stmt = (
            select(Opportunity, Instrument)
            .join(Instrument, Opportunity.instrument_id == Instrument.id)
            .where(Opportunity.status == OpportunityStatus.CONFIRM_FAILED)
            .order_by(Opportunity.updated_at.desc())
            .limit(limit)
        )
        if strategy:
            stmt = stmt.where(Opportunity.strategy == strategy.upper())
        if direction:
            stmt = stmt.where(Opportunity.side == OpportunitySide(direction.upper()))
        if tier is not None:
            stmt = stmt.where(Instrument.tier == tier)
        if date_from is not None:
            stmt = stmt.where(Opportunity.updated_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(Opportunity.updated_at <= date_to)

        rows = self._session.execute(stmt).all()
        scores = self._load_latest_scores([opp.id for opp, _ in rows])
        items: list[dict[str, Any]] = []
        for opp, inst in rows:
            entry = float(opp.entry_price)
            ctx = opp.context or {}
            atr_value = ctx.get("atr_value")
            sl_mult = ctx.get("sl_multiplier")
            tp_mult = ctx.get("tp_multiplier")
            sl_price = str(opp.stop_price) if opp.stop_price else str(entry)
            tp_price = str(opp.take_profit_price) if opp.take_profit_price else str(entry)
            sl_pct = abs(float(sl_price) - entry) / entry * 100 if entry > 0 else 0.0
            tp_pct = abs(float(tp_price) - entry) / entry * 100 if entry > 0 else 0.0
            tier_val = inst.tier or 3
            score_row = scores.get(opp.id)
            grade = None
            if score_row and score_row.factors:
                grade = score_row.factors.get("grade")
            items.append({
                "id": -(opp.id + 1_000_000),
                "opportunity_id": opp.id,
                "symbol": inst.inst_id,
                "strategy_type": opp.strategy,
                "direction": opp.side.value,
                "entry_price": str(opp.entry_price),
                "tp_price": tp_price,
                "sl_price": sl_price,
                "tp_pct": round(tp_pct, 4),
                "sl_pct": round(sl_pct, 4),
                "timeout_hours": 0,
                "status": "CONFIRM_FAILED",
                "entry_at": opp.updated_at.isoformat(),
                "closed_at": opp.updated_at.isoformat(),
                "close_price": None,
                "pnl_pct": None,
                "tier": tier_val,
                "duration_seconds": None,
                "atr_value": float(atr_value) if atr_value is not None else None,
                "sl_multiplier": float(sl_mult) if sl_mult is not None else None,
                "tp_multiplier": float(tp_mult) if tp_mult is not None else None,
                "signal_price": str(opp.entry_price),
                "confirmed_at": None,
                "confirmation_required": True,
                "confirmation_status": "FAILED",
                "total_score": score_row.total_score if score_row else None,
                "grade": grade,
            })
        return items

    def get_stats(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Aggregate paper trade performance statistics."""
        all_trades = list(self._session.scalars(select(PaperTrade)).all())
        if date_from is not None:
            all_trades = [t for t in all_trades if t.entry_at >= date_from]
        if date_to is not None:
            all_trades = [t for t in all_trades if t.entry_at <= date_to]
        closed = [
            t for t in all_trades
            if t.status in (PaperTradeStatus.WIN, PaperTradeStatus.LOSS, PaperTradeStatus.EXPIRED)
        ]
        running = sum(1 for t in all_trades if t.status == PaperTradeStatus.RUNNING)
        wins = sum(1 for t in closed if t.status == PaperTradeStatus.WIN)
        losses = sum(1 for t in closed if t.status == PaperTradeStatus.LOSS)
        expired = sum(1 for t in closed if t.status == PaperTradeStatus.EXPIRED)

        closed_with_pnl = [t for t in closed if t.pnl_pct is not None]
        avg_pnl = (
            float(sum(t.pnl_pct for t in closed_with_pnl) / len(closed_with_pnl))
            if closed_with_pnl
            else 0.0
        )
        win_rate = (wins / len(closed) * 100) if closed else 0.0

        by_strategy = self._group_stats(all_trades, lambda t: t.strategy_type)
        by_tier = self._group_stats(all_trades, lambda t: str(t.tier))

        best = max(closed_with_pnl, key=lambda t: t.pnl_pct, default=None)
        worst = min(closed_with_pnl, key=lambda t: t.pnl_pct, default=None)

        confirm_stats = self._confirmation_stats(all_trades)

        return {
            "total_trades": len(all_trades),
            "running": running,
            "wins": wins,
            "losses": losses,
            "expired": expired,
            "win_rate": round(win_rate, 2),
            "avg_pnl": round(avg_pnl, 4),
            "by_strategy": by_strategy,
            "by_tier": by_tier,
            "best_trade": self._to_dict(best) if best else None,
            "worst_trade": self._to_dict(worst) if worst else None,
            "pnl_by_day": self._pnl_by_day(closed_with_pnl),
            **confirm_stats,
        }

    def _confirmation_stats(self, trades: list[PaperTrade]) -> dict[str, Any]:
        """Aggregate M15 confirmation metrics."""
        required = [t for t in trades if t.confirmation_required]
        confirmed = [t for t in required if t.confirmed_at is not None]
        instant = [t for t in trades if not t.confirmation_required]

        wait_minutes: list[float] = []
        for trade in confirmed:
            if trade.confirmed_at and trade.signal_price:
                wait_minutes.append(
                    (trade.confirmed_at - trade.entry_at).total_seconds() / 60,
                )

        failed = self._session.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.status == OpportunityStatus.CONFIRM_FAILED),
        ) or 0
        pending = self._session.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.status == OpportunityStatus.PENDING_CONFIRM),
        ) or 0

        total_signals = len(instant) + len(required) + int(failed)
        confirm_rate = (len(confirmed) / len(required) * 100) if required else 0.0
        fail_rate = (int(failed) / (len(required) + int(failed)) * 100) if (required or failed) else 0.0

        return {
            "confirmation_rate": round(confirm_rate, 2),
            "avg_confirm_minutes": round(sum(wait_minutes) / len(wait_minutes), 2) if wait_minutes else 0.0,
            "confirm_failed_rate": round(fail_rate, 2),
            "pending_confirmations": int(pending),
            "instant_trades": len(instant),
            "confirmed_trades": len(confirmed),
            "confirm_failed_count": int(failed),
        }

    @staticmethod
    def _group_stats(
        trades: list[PaperTrade],
        key_fn: Any,
    ) -> dict[str, dict[str, Any]]:
        groups: dict[str, list[PaperTrade]] = {}
        for trade in trades:
            key = str(key_fn(trade))
            groups.setdefault(key, []).append(trade)

        result: dict[str, dict[str, Any]] = {}
        for key, items in groups.items():
            closed = [
                t for t in items
                if t.status in (
                    PaperTradeStatus.WIN,
                    PaperTradeStatus.LOSS,
                    PaperTradeStatus.EXPIRED,
                )
            ]
            wins = sum(1 for t in closed if t.status == PaperTradeStatus.WIN)
            running = sum(1 for t in items if t.status == PaperTradeStatus.RUNNING)
            pnls = [t for t in closed if t.pnl_pct is not None]
            result[key] = {
                "count": len(items),
                "closed": len(closed),
                "wins": wins,
                "running": running,
                "win_rate": round(wins / len(closed) * 100, 2) if closed else 0.0,
                "avg_pnl": round(
                    float(sum(t.pnl_pct for t in pnls) / len(pnls)), 4,
                ) if pnls else 0.0,
            }
        return result

    @staticmethod
    def _pnl_by_day(closed: list[PaperTrade]) -> list[dict[str, Any]]:
        """Build cumulative P&L series grouped by close date."""
        if not closed:
            return []

        by_day: dict[str, float] = {}
        for trade in sorted(closed, key=lambda t: t.closed_at or t.entry_at):
            day = (trade.closed_at or trade.entry_at).strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0.0) + float(trade.pnl_pct or 0)

        cumulative = 0.0
        series: list[dict[str, Any]] = []
        for day in sorted(by_day):
            daily = by_day[day]
            cumulative += daily
            series.append({
                "date": day,
                "daily_pnl": round(daily, 4),
                "cumulative_pnl": round(cumulative, 4),
            })
        return series

    @staticmethod
    def _to_dict(
        row: PaperTrade,
        score: OpportunityScore | None = None,
    ) -> dict[str, Any]:
        duration_seconds: float | None = None
        if row.closed_at is not None:
            duration_seconds = (row.closed_at - row.entry_at).total_seconds()

        grade = None
        total_score = None
        if score is not None:
            total_score = score.total_score
            if score.factors:
                grade = score.factors.get("grade")

        return {
            "id": row.id,
            "opportunity_id": row.opportunity_id,
            "symbol": row.symbol,
            "strategy_type": row.strategy_type,
            "direction": row.direction.value,
            "entry_price": str(row.entry_price),
            "tp_price": str(row.tp_price),
            "sl_price": str(row.sl_price),
            "tp_pct": float(row.tp_pct),
            "sl_pct": float(row.sl_pct),
            "timeout_hours": row.timeout_hours,
            "status": row.status.value,
            "entry_at": row.entry_at.isoformat(),
            "closed_at": row.closed_at.isoformat() if row.closed_at else None,
            "close_price": str(row.close_price) if row.close_price is not None else None,
            "pnl_pct": float(row.pnl_pct) if row.pnl_pct is not None else None,
            "tier": row.tier,
            "duration_seconds": duration_seconds,
            "atr_value": float(row.atr_value) if row.atr_value is not None else None,
            "sl_multiplier": float(row.sl_multiplier) if row.sl_multiplier is not None else None,
            "tp_multiplier": float(row.tp_multiplier) if row.tp_multiplier is not None else None,
            "signal_price": str(row.signal_price) if row.signal_price is not None else None,
            "confirmed_at": row.confirmed_at.isoformat() if row.confirmed_at else None,
            "confirmation_required": row.confirmation_required,
            "confirmation_status": PaperTradeRepository._confirmation_status(row),
            "total_score": total_score,
            "grade": grade,
        }

    @staticmethod
    def _confirmation_status(row: PaperTrade) -> str:
        if not row.confirmation_required:
            return "INSTANT"
        if row.confirmed_at is not None:
            return "CONFIRMED"
        return "INSTANT"
