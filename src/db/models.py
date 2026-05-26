"""SQLAlchemy ORM models for the OKX scanner.

Six tables modelling the full opportunity lifecycle:

1. :class:`Instrument`         — tradable symbols (BTC-USDT, ETH-USDT, ...)
2. :class:`MarketSnapshot`     — periodic market data captures
3. :class:`Opportunity`        — detected setups
4. :class:`OpportunityScore`   — multi-factor scoring per opportunity
5. :class:`RiskDecision`       — risk-engine approve/reject record
6. :class:`Alert`              — outbound notifications dispatched
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class InstrumentType(str, enum.Enum):
    """OKX instrument category."""

    SPOT = "SPOT"
    MARGIN = "MARGIN"
    SWAP = "SWAP"
    FUTURES = "FUTURES"
    OPTION = "OPTION"


class OpportunityStatus(str, enum.Enum):
    """Lifecycle status of an opportunity."""

    DETECTED = "DETECTED"
    SCORED = "SCORED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ALERTED = "ALERTED"
    EXPIRED = "EXPIRED"
    PENDING_CONFIRM = "PENDING_CONFIRM"
    CONFIRM_FAILED = "CONFIRM_FAILED"


class OpportunitySide(str, enum.Enum):
    """Trade direction."""

    LONG = "LONG"
    SHORT = "SHORT"


class RiskOutcome(str, enum.Enum):
    """Risk-engine decision."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AlertChannel(str, enum.Enum):
    """Outbound alert channels."""

    TELEGRAM = "TELEGRAM"
    WEBHOOK = "WEBHOOK"
    EMAIL = "EMAIL"


class AlertStatus(str, enum.Enum):
    """Alert dispatch status."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class PaperTradeStatus(str, enum.Enum):
    """Paper trade lifecycle status."""

    RUNNING = "RUNNING"
    WIN = "WIN"
    LOSS = "LOSS"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class StrategySensitivity(str, enum.Enum):
    """Strategy detection sensitivity."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Declarative base. All models inherit from this."""

    type_annotation_map = {
        dict: JSONB,
    }


# ---------------------------------------------------------------------------
# 1. Instrument
# ---------------------------------------------------------------------------
class Instrument(Base):
    """A tradable OKX instrument (e.g. ``BTC-USDT``).

    Source of truth for the universe we scan. Synced from OKX
    ``GET /api/v5/public/instruments`` periodically.
    """

    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    inst_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    inst_type: Mapped[InstrumentType] = mapped_column(
        SAEnum(InstrumentType, name="instrument_type_enum"),
        nullable=False,
        index=True,
    )
    base_ccy: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quote_ccy: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    settle_ccy: Mapped[str | None] = mapped_column(String(32))
    tick_size: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    lot_size: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    min_size: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    contract_value: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    tier: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    scan_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expiry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    snapshots: Mapped[list["MarketSnapshot"]] = relationship(
        back_populates="instrument", cascade="all, delete-orphan", passive_deletes=True
    )
    opportunities: Mapped[list["Opportunity"]] = relationship(
        back_populates="instrument", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_instruments_active_type", "is_active", "inst_type"),
        Index("ix_instruments_quote_active", "quote_ccy", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Instrument {self.inst_id} ({self.inst_type.value})>"


# ---------------------------------------------------------------------------
# 2. MarketSnapshot
# ---------------------------------------------------------------------------
class MarketSnapshot(Base):
    """A point-in-time view of the order-book / ticker for one instrument."""

    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    last_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    bid_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    ask_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    bid_size: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    ask_size: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))

    open_24h: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    high_24h: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    low_24h: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    volume_24h_base: Mapped[Decimal | None] = mapped_column(Numeric(36, 12))
    volume_24h_quote: Mapped[Decimal | None] = mapped_column(Numeric(36, 12))

    open_interest: Mapped[Decimal | None] = mapped_column(Numeric(36, 12))
    funding_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 12))

    raw: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    instrument: Mapped["Instrument"] = relationship(back_populates="snapshots")

    __table_args__ = (
        Index("ix_market_snapshots_inst_time", "instrument_id", "captured_at"),
        CheckConstraint("last_price >= 0", name="ck_market_snapshots_last_price_nonneg"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketSnapshot inst={self.instrument_id} "
            f"last={self.last_price} at={self.captured_at.isoformat()}>"
        )


# ---------------------------------------------------------------------------
# 3. Opportunity
# ---------------------------------------------------------------------------
class Opportunity(Base):
    """A trading setup detected by a strategy."""

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    strategy: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    side: Mapped[OpportunitySide] = mapped_column(
        SAEnum(OpportunitySide, name="opportunity_side_enum"), nullable=False
    )
    status: Mapped[OpportunityStatus] = mapped_column(
        SAEnum(OpportunityStatus, name="opportunity_status_enum"),
        nullable=False,
        default=OpportunityStatus.DETECTED,
        index=True,
    )

    entry_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    take_profit_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    expected_rr: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    context: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    instrument: Mapped["Instrument"] = relationship(back_populates="opportunities")
    scores: Mapped[list["OpportunityScore"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan", passive_deletes=True
    )
    risk_decisions: Mapped[list["RiskDecision"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan", passive_deletes=True
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan", passive_deletes=True
    )
    paper_trades: Mapped[list["PaperTrade"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_opportunities_status_detected", "status", "detected_at"),
        Index("ix_opportunities_strategy_detected", "strategy", "detected_at"),
        CheckConstraint("entry_price > 0", name="ck_opportunities_entry_price_positive"),
    )

    def __repr__(self) -> str:
        return (
            f"<Opportunity id={self.id} inst={self.instrument_id} "
            f"strategy={self.strategy} side={self.side.value} status={self.status.value}>"
        )


# ---------------------------------------------------------------------------
# 4. OpportunityScore
# ---------------------------------------------------------------------------
class OpportunityScore(Base):
    """Multi-factor score attached to an opportunity (0-100)."""

    __tablename__ = "opportunity_scores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    total_score: Mapped[int] = mapped_column(Integer, nullable=False)

    trend_score: Mapped[int | None] = mapped_column(Integer)
    momentum_score: Mapped[int | None] = mapped_column(Integer)
    volume_score: Mapped[int | None] = mapped_column(Integer)
    volatility_score: Mapped[int | None] = mapped_column(Integer)
    liquidity_score: Mapped[int | None] = mapped_column(Integer)

    factors: Mapped[dict | None] = mapped_column(JSONB)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")

    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    opportunity: Mapped["Opportunity"] = relationship(back_populates="scores")

    __table_args__ = (
        UniqueConstraint("opportunity_id", "model_version", name="uq_scores_opp_model"),
        CheckConstraint("total_score BETWEEN 0 AND 100", name="ck_scores_total_range"),
    )

    def __repr__(self) -> str:
        return (
            f"<OpportunityScore opp={self.opportunity_id} total={self.total_score} "
            f"model={self.model_version}>"
        )


# ---------------------------------------------------------------------------
# 5. RiskDecision
# ---------------------------------------------------------------------------
class RiskDecision(Base):
    """Decision returned by the risk engine for an opportunity."""

    __tablename__ = "risk_decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    outcome: Mapped[RiskOutcome] = mapped_column(
        SAEnum(RiskOutcome, name="risk_outcome_enum"), nullable=False, index=True
    )
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason_detail: Mapped[str | None] = mapped_column(Text)

    position_size_usd: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    max_risk_usd: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))

    snapshot: Mapped[dict | None] = mapped_column(JSONB)

    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    opportunity: Mapped["Opportunity"] = relationship(back_populates="risk_decisions")

    __table_args__ = (
        Index("ix_risk_decisions_outcome_time", "outcome", "decided_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<RiskDecision opp={self.opportunity_id} outcome={self.outcome.value} "
            f"reason={self.reason_code}>"
        )


# ---------------------------------------------------------------------------
# 6. Alert
# ---------------------------------------------------------------------------
class Alert(Base):
    """An outbound alert dispatched (or attempted) for an opportunity."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[AlertChannel] = mapped_column(
        SAEnum(AlertChannel, name="alert_channel_enum"), nullable=False, index=True
    )
    status: Mapped[AlertStatus] = mapped_column(
        SAEnum(AlertStatus, name="alert_status_enum"),
        nullable=False,
        default=AlertStatus.PENDING,
        index=True,
    )

    target: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    opportunity: Mapped["Opportunity"] = relationship(back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_status_created", "status", "created_at"),
        Index("ix_alerts_channel_status", "channel", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Alert id={self.id} opp={self.opportunity_id} "
            f"channel={self.channel.value} status={self.status.value}>"
        )


# ---------------------------------------------------------------------------
# 7. PaperTrade
# ---------------------------------------------------------------------------
class PaperTrade(Base):
    """Simulated trade opened when an opportunity is approved."""

    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    strategy_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    direction: Mapped[OpportunitySide] = mapped_column(
        SAEnum(OpportunitySide, name="opportunity_side_enum"), nullable=False
    )

    entry_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    tp_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    sl_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    tp_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    sl_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    timeout_hours: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[PaperTradeStatus] = mapped_column(
        SAEnum(PaperTradeStatus, name="paper_trade_status_enum"),
        nullable=False,
        default=PaperTradeStatus.RUNNING,
        index=True,
    )

    entry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    tier: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    atr_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    sl_multiplier: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    tp_multiplier: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    signal_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    opportunity: Mapped["Opportunity"] = relationship(back_populates="paper_trades")

    __table_args__ = (
        CheckConstraint("entry_price > 0", name="ck_paper_trades_entry_price_positive"),
        CheckConstraint("tier >= 1 AND tier <= 3", name="ck_paper_trades_tier_range"),
    )

    def __repr__(self) -> str:
        return (
            f"<PaperTrade id={self.id} symbol={self.symbol} "
            f"status={self.status.value} pnl={self.pnl_pct}>"
        )


# ---------------------------------------------------------------------------
# 8. StrategySettings
# ---------------------------------------------------------------------------
class StrategySettings(Base):
    """Per-strategy risk profile and paper-trade parameters."""

    __tablename__ = "strategy_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy_type: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_concurrent: Mapped[int] = mapped_column(Integer, nullable=False)
    cooldown_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    sensitivity: Mapped[StrategySensitivity] = mapped_column(
        SAEnum(StrategySensitivity, name="strategy_sensitivity_enum"),
        nullable=False,
    )
    tp_tier1: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    tp_tier2: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    tp_tier3: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    sl_tier1: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    sl_tier2: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    sl_tier3: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    timeout_tier1: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_tier2: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_tier3: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    real_trading_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmation_candles: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    atr_sl_multiplier_t1: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    atr_sl_multiplier_t2: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    atr_sl_multiplier_t3: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    atr_tp_multiplier_t1: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    atr_tp_multiplier_t2: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    atr_tp_multiplier_t3: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("min_score >= 50 AND min_score <= 95", name="ck_strategy_settings_min_score"),
        CheckConstraint(
            "max_concurrent >= 1 AND max_concurrent <= 10",
            name="ck_strategy_settings_max_concurrent",
        ),
        CheckConstraint(
            "cooldown_hours >= 0.5 AND cooldown_hours <= 24",
            name="ck_strategy_settings_cooldown",
        ),
        CheckConstraint("tp_tier1 > sl_tier1", name="ck_strategy_settings_tp_sl_t1"),
        CheckConstraint("tp_tier2 > sl_tier2", name="ck_strategy_settings_tp_sl_t2"),
        CheckConstraint("tp_tier3 > sl_tier3", name="ck_strategy_settings_tp_sl_t3"),
    )

    def tier_atr_params(self, tier: int) -> dict[str, float | int]:
        """Return ATR multipliers and timeout for instrument tier (1–3)."""
        idx = max(1, min(3, tier))
        return {
            "sl_multiplier": float(getattr(self, f"atr_sl_multiplier_t{idx}")),
            "tp_multiplier": float(getattr(self, f"atr_tp_multiplier_t{idx}")),
            "timeout_hours": int(getattr(self, f"timeout_tier{idx}")),
        }

    def tier_params(self, tier: int) -> dict[str, float | int]:
        """Return legacy percent TP/SL (fallback when ATR unavailable)."""
        idx = max(1, min(3, tier))
        return {
            "tp_pct": float(getattr(self, f"tp_tier{idx}")),
            "sl_pct": float(getattr(self, f"sl_tier{idx}")),
            "timeout_hours": int(getattr(self, f"timeout_tier{idx}")),
        }

    def __repr__(self) -> str:
        return f"<StrategySettings strategy={self.strategy_type} enabled={self.is_enabled}>"


# ---------------------------------------------------------------------------
# 9. SystemConfig
# ---------------------------------------------------------------------------
class SystemConfig(Base):
    """Singleton row for global scanner/dashboard settings."""

    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    max_total_concurrent_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    alert_min_score: Mapped[int] = mapped_column(Integer, nullable=False, default=65)
    auto_refresh_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_system_config_singleton"),
        CheckConstraint(
            "max_total_concurrent_trades >= 5 AND max_total_concurrent_trades <= 50",
            name="ck_system_config_max_concurrent",
        ),
        CheckConstraint(
            "alert_min_score >= 50 AND alert_min_score <= 95",
            name="ck_system_config_alert_min_score",
        ),
    )


class TradingMode(str, enum.Enum):
    PAPER = "paper"
    REAL = "real"


class TradingConfig(Base):
    __tablename__ = "trading_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    mode: Mapped[str] = mapped_column(String(10), default=TradingMode.PAPER.value)
    api_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    api_secret: Mapped[str | None] = mapped_column(String(256), nullable=True)
    api_passphrase: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # Risk controls
    daily_loss_limit_pct: Mapped[float] = mapped_column(default=5.0)   # stop if daily loss > X%
    size_pct_tier1: Mapped[float] = mapped_column(default=3.0)          # % balance per trade T1
    size_pct_tier2: Mapped[float] = mapped_column(default=2.0)          # % balance per trade T2
    size_pct_tier3: Mapped[float] = mapped_column(default=1.0)          # % balance per trade T3
    max_leverage: Mapped[int] = mapped_column(default=5)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
