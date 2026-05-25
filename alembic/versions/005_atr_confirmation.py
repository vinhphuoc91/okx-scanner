"""ATR-based SL/TP and M15 confirmation delay.

Revision ID: 005
Revises: 004
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ATR_DEFAULTS: dict[str, dict] = {
    "FUNDING": {
        "requires_confirmation": False,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 1.5,
        "atr_sl_multiplier_t2": 2.0,
        "atr_sl_multiplier_t3": 2.5,
        "atr_tp_multiplier_t1": 3.0,
        "atr_tp_multiplier_t2": 4.0,
        "atr_tp_multiplier_t3": 5.0,
    },
    "MOMENTUM": {
        "requires_confirmation": True,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 2.0,
        "atr_sl_multiplier_t2": 2.5,
        "atr_sl_multiplier_t3": 3.0,
        "atr_tp_multiplier_t1": 4.0,
        "atr_tp_multiplier_t2": 5.0,
        "atr_tp_multiplier_t3": 6.0,
    },
    "BREAKOUT": {
        "requires_confirmation": True,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 2.5,
        "atr_sl_multiplier_t2": 3.0,
        "atr_sl_multiplier_t3": 3.5,
        "atr_tp_multiplier_t1": 5.0,
        "atr_tp_multiplier_t2": 6.0,
        "atr_tp_multiplier_t3": 7.0,
    },
    "VOLUME_ANOMALY": {
        "requires_confirmation": False,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 1.5,
        "atr_sl_multiplier_t2": 2.0,
        "atr_sl_multiplier_t3": 2.5,
        "atr_tp_multiplier_t1": 3.0,
        "atr_tp_multiplier_t2": 4.0,
        "atr_tp_multiplier_t3": 5.0,
    },
    "TREND_PULLBACK": {
        "requires_confirmation": True,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 2.0,
        "atr_sl_multiplier_t2": 2.5,
        "atr_sl_multiplier_t3": 3.0,
        "atr_tp_multiplier_t1": 4.0,
        "atr_tp_multiplier_t2": 5.0,
        "atr_tp_multiplier_t3": 6.0,
    },
}


def upgrade() -> None:
    op.execute(
        "ALTER TYPE opportunity_status_enum ADD VALUE IF NOT EXISTS 'PENDING_CONFIRM'",
    )
    op.execute(
        "ALTER TYPE opportunity_status_enum ADD VALUE IF NOT EXISTS 'CONFIRM_FAILED'",
    )

    op.add_column(
        "paper_trades",
        sa.Column("atr_value", sa.Numeric(precision=24, scale=8), nullable=True),
    )
    op.add_column(
        "paper_trades",
        sa.Column("sl_multiplier", sa.Numeric(precision=6, scale=2), nullable=True),
    )
    op.add_column(
        "paper_trades",
        sa.Column("tp_multiplier", sa.Numeric(precision=6, scale=2), nullable=True),
    )
    op.add_column(
        "paper_trades",
        sa.Column("signal_price", sa.Numeric(precision=24, scale=8), nullable=True),
    )
    op.add_column(
        "paper_trades",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "paper_trades",
        sa.Column(
            "confirmation_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.add_column(
        "strategy_settings",
        sa.Column(
            "requires_confirmation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "strategy_settings",
        sa.Column("confirmation_candles", sa.Integer(), nullable=False, server_default="1"),
    )
    for tier in (1, 2, 3):
        op.add_column(
            "strategy_settings",
            sa.Column(
                f"atr_sl_multiplier_t{tier}",
                sa.Numeric(precision=4, scale=2),
                nullable=False,
                server_default="2.0",
            ),
        )
        op.add_column(
            "strategy_settings",
            sa.Column(
                f"atr_tp_multiplier_t{tier}",
                sa.Numeric(precision=4, scale=2),
                nullable=False,
                server_default="4.0",
            ),
        )

    bind = op.get_bind()
    for strategy_type, values in _ATR_DEFAULTS.items():
        sets = ", ".join(f"{col} = :{col}" for col in values)
        bind.execute(
            sa.text(
                f"UPDATE strategy_settings SET {sets} WHERE strategy_type = :strategy_type",
            ),
            {"strategy_type": strategy_type, **values},
        )


def downgrade() -> None:
    op.drop_column("strategy_settings", "atr_tp_multiplier_t3")
    op.drop_column("strategy_settings", "atr_tp_multiplier_t2")
    op.drop_column("strategy_settings", "atr_tp_multiplier_t1")
    op.drop_column("strategy_settings", "atr_sl_multiplier_t3")
    op.drop_column("strategy_settings", "atr_sl_multiplier_t2")
    op.drop_column("strategy_settings", "atr_sl_multiplier_t1")
    op.drop_column("strategy_settings", "confirmation_candles")
    op.drop_column("strategy_settings", "requires_confirmation")

    op.drop_column("paper_trades", "confirmation_required")
    op.drop_column("paper_trades", "confirmed_at")
    op.drop_column("paper_trades", "signal_price")
    op.drop_column("paper_trades", "tp_multiplier")
    op.drop_column("paper_trades", "sl_multiplier")
    op.drop_column("paper_trades", "atr_value")
