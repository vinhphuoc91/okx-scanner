"""Initial schema — six core tables.

Revision ID: 001
Revises:
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INSTRUMENT_TYPE_ENUM = postgresql.ENUM(
    "SPOT", "MARGIN", "SWAP", "FUTURES", "OPTION",
    name="instrument_type_enum",
    create_type=False,
)
OPPORTUNITY_STATUS_ENUM = postgresql.ENUM(
    "DETECTED", "SCORED", "APPROVED", "REJECTED", "ALERTED", "EXPIRED",
    name="opportunity_status_enum",
    create_type=False,
)
OPPORTUNITY_SIDE_ENUM = postgresql.ENUM(
    "LONG", "SHORT",
    name="opportunity_side_enum",
    create_type=False,
)
RISK_OUTCOME_ENUM = postgresql.ENUM(
    "APPROVED", "REJECTED",
    name="risk_outcome_enum",
    create_type=False,
)
ALERT_CHANNEL_ENUM = postgresql.ENUM(
    "TELEGRAM", "WEBHOOK", "EMAIL",
    name="alert_channel_enum",
    create_type=False,
)
ALERT_STATUS_ENUM = postgresql.ENUM(
    "PENDING", "SENT", "FAILED",
    name="alert_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    INSTRUMENT_TYPE_ENUM.create(bind, checkfirst=True)
    OPPORTUNITY_STATUS_ENUM.create(bind, checkfirst=True)
    OPPORTUNITY_SIDE_ENUM.create(bind, checkfirst=True)
    RISK_OUTCOME_ENUM.create(bind, checkfirst=True)
    ALERT_CHANNEL_ENUM.create(bind, checkfirst=True)
    ALERT_STATUS_ENUM.create(bind, checkfirst=True)

    op.create_table(
        "instruments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("inst_id", sa.String(length=64), nullable=False),
        sa.Column("inst_type", INSTRUMENT_TYPE_ENUM, nullable=False),
        sa.Column("base_ccy", sa.String(length=32), nullable=False),
        sa.Column("quote_ccy", sa.String(length=32), nullable=False),
        sa.Column("settle_ccy", sa.String(length=32), nullable=True),
        sa.Column("tick_size", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("lot_size", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("min_size", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("contract_value", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("listed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inst_id"),
    )
    op.create_index("ix_instruments_active_type", "instruments", ["is_active", "inst_type"])
    op.create_index("ix_instruments_base_ccy", "instruments", ["base_ccy"])
    op.create_index("ix_instruments_inst_id", "instruments", ["inst_id"])
    op.create_index("ix_instruments_inst_type", "instruments", ["inst_type"])
    op.create_index("ix_instruments_is_active", "instruments", ["is_active"])
    op.create_index("ix_instruments_quote_active", "instruments", ["quote_ccy", "is_active"])
    op.create_index("ix_instruments_quote_ccy", "instruments", ["quote_ccy"])

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_price", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("bid_price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("ask_price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("bid_size", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("ask_size", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("open_24h", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("high_24h", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("low_24h", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("volume_24h_base", sa.Numeric(precision=36, scale=12), nullable=True),
        sa.Column("volume_24h_quote", sa.Numeric(precision=36, scale=12), nullable=True),
        sa.Column("open_interest", sa.Numeric(precision=36, scale=12), nullable=True),
        sa.Column("funding_rate", sa.Numeric(precision=18, scale=12), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("last_price >= 0", name="ck_market_snapshots_last_price_nonneg"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_snapshots_captured_at", "market_snapshots", ["captured_at"])
    op.create_index("ix_market_snapshots_inst_time", "market_snapshots", ["instrument_id", "captured_at"])
    op.create_index("ix_market_snapshots_instrument_id", "market_snapshots", ["instrument_id"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("side", OPPORTUNITY_SIDE_ENUM, nullable=False),
        sa.Column(
            "status",
            OPPORTUNITY_STATUS_ENUM,
            nullable=False,
            server_default="DETECTED",
        ),
        sa.Column("entry_price", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("stop_price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("take_profit_price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("expected_rr", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("entry_price > 0", name="ck_opportunities_entry_price_positive"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_detected_at", "opportunities", ["detected_at"])
    op.create_index("ix_opportunities_instrument_id", "opportunities", ["instrument_id"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])
    op.create_index("ix_opportunities_status_detected", "opportunities", ["status", "detected_at"])
    op.create_index("ix_opportunities_strategy", "opportunities", ["strategy"])
    op.create_index("ix_opportunities_strategy_detected", "opportunities", ["strategy", "detected_at"])

    op.create_table(
        "opportunity_scores",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("trend_score", sa.Integer(), nullable=True),
        sa.Column("momentum_score", sa.Integer(), nullable=True),
        sa.Column("volume_score", sa.Integer(), nullable=True),
        sa.Column("volatility_score", sa.Integer(), nullable=True),
        sa.Column("liquidity_score", sa.Integer(), nullable=True),
        sa.Column("factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column(
            "scored_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("total_score BETWEEN 0 AND 100", name="ck_scores_total_range"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", "model_version", name="uq_scores_opp_model"),
    )
    op.create_index("ix_opportunity_scores_opportunity_id", "opportunity_scores", ["opportunity_id"])
    op.create_index("ix_opportunity_scores_scored_at", "opportunity_scores", ["scored_at"])

    op.create_table(
        "risk_decisions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("outcome", RISK_OUTCOME_ENUM, nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        sa.Column("position_size_usd", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("max_risk_usd", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_decisions_decided_at", "risk_decisions", ["decided_at"])
    op.create_index("ix_risk_decisions_opportunity_id", "risk_decisions", ["opportunity_id"])
    op.create_index("ix_risk_decisions_outcome", "risk_decisions", ["outcome"])
    op.create_index("ix_risk_decisions_outcome_time", "risk_decisions", ["outcome", "decided_at"])
    op.create_index("ix_risk_decisions_reason_code", "risk_decisions", ["reason_code"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("channel", ALERT_CHANNEL_ENUM, nullable=False),
        sa.Column(
            "status",
            ALERT_STATUS_ENUM,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_channel", "alerts", ["channel"])
    op.create_index("ix_alerts_channel_status", "alerts", ["channel", "status"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])
    op.create_index("ix_alerts_opportunity_id", "alerts", ["opportunity_id"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_status_created", "alerts", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("risk_decisions")
    op.drop_table("opportunity_scores")
    op.drop_table("opportunities")
    op.drop_table("market_snapshots")
    op.drop_table("instruments")

    bind = op.get_bind()
    ALERT_STATUS_ENUM.drop(bind, checkfirst=True)
    ALERT_CHANNEL_ENUM.drop(bind, checkfirst=True)
    RISK_OUTCOME_ENUM.drop(bind, checkfirst=True)
    OPPORTUNITY_SIDE_ENUM.drop(bind, checkfirst=True)
    OPPORTUNITY_STATUS_ENUM.drop(bind, checkfirst=True)
    INSTRUMENT_TYPE_ENUM.drop(bind, checkfirst=True)
