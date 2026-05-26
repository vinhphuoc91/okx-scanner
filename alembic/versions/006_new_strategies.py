"""Seed strategy settings for three advanced strategies.

Revision ID: 006
Revises: 005
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_sensitivity_enum = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    name="strategy_sensitivity_enum",
    create_type=False,
)

_NEW_STRATEGIES: list[dict] = [
    {
        "strategy_type": "CORRELATION_DIVERGENCE",
        "is_enabled": True,
        "min_score": 70,
        "max_concurrent": 3,
        "cooldown_hours": 2.0,
        "sensitivity": "MEDIUM",
        "tp_tier1": 3.0,
        "tp_tier2": 4.0,
        "tp_tier3": 5.0,
        "sl_tier1": 1.5,
        "sl_tier2": 2.0,
        "sl_tier3": 2.5,
        "timeout_tier1": 8,
        "timeout_tier2": 12,
        "timeout_tier3": 24,
        "requires_confirmation": False,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 1.5,
        "atr_sl_multiplier_t2": 2.0,
        "atr_sl_multiplier_t3": 2.5,
        "atr_tp_multiplier_t1": 3.0,
        "atr_tp_multiplier_t2": 4.0,
        "atr_tp_multiplier_t3": 5.0,
    },
    {
        "strategy_type": "LIQUIDATION_ZONE",
        "is_enabled": True,
        "min_score": 75,
        "max_concurrent": 2,
        "cooldown_hours": 4.0,
        "sensitivity": "LOW",
        "tp_tier1": 4.0,
        "tp_tier2": 5.0,
        "tp_tier3": 6.0,
        "sl_tier1": 2.0,
        "sl_tier2": 2.5,
        "sl_tier3": 3.0,
        "timeout_tier1": 8,
        "timeout_tier2": 12,
        "timeout_tier3": 24,
        "requires_confirmation": True,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 2.0,
        "atr_sl_multiplier_t2": 2.5,
        "atr_sl_multiplier_t3": 3.0,
        "atr_tp_multiplier_t1": 4.0,
        "atr_tp_multiplier_t2": 5.0,
        "atr_tp_multiplier_t3": 6.0,
    },
    {
        "strategy_type": "STAT_ARBITRAGE",
        "is_enabled": True,
        "min_score": 72,
        "max_concurrent": 3,
        "cooldown_hours": 1.0,
        "sensitivity": "MEDIUM",
        "tp_tier1": 2.0,
        "tp_tier2": 3.0,
        "tp_tier3": 4.0,
        "sl_tier1": 1.0,
        "sl_tier2": 1.5,
        "sl_tier3": 2.0,
        "timeout_tier1": 6,
        "timeout_tier2": 8,
        "timeout_tier3": 12,
        "requires_confirmation": False,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 1.0,
        "atr_sl_multiplier_t2": 1.5,
        "atr_sl_multiplier_t3": 2.0,
        "atr_tp_multiplier_t1": 2.0,
        "atr_tp_multiplier_t2": 3.0,
        "atr_tp_multiplier_t3": 4.0,
    },
]


def upgrade() -> None:
    strategy_settings = sa.table(
        "strategy_settings",
        sa.column("strategy_type", sa.String),
        sa.column("is_enabled", sa.Boolean),
        sa.column("min_score", sa.Integer),
        sa.column("max_concurrent", sa.Integer),
        sa.column("cooldown_hours", sa.Numeric),
        sa.column("sensitivity", _sensitivity_enum),
        sa.column("tp_tier1", sa.Numeric),
        sa.column("tp_tier2", sa.Numeric),
        sa.column("tp_tier3", sa.Numeric),
        sa.column("sl_tier1", sa.Numeric),
        sa.column("sl_tier2", sa.Numeric),
        sa.column("sl_tier3", sa.Numeric),
        sa.column("timeout_tier1", sa.Integer),
        sa.column("timeout_tier2", sa.Integer),
        sa.column("timeout_tier3", sa.Integer),
        sa.column("requires_confirmation", sa.Boolean),
        sa.column("confirmation_candles", sa.Integer),
        sa.column("atr_sl_multiplier_t1", sa.Numeric),
        sa.column("atr_sl_multiplier_t2", sa.Numeric),
        sa.column("atr_sl_multiplier_t3", sa.Numeric),
        sa.column("atr_tp_multiplier_t1", sa.Numeric),
        sa.column("atr_tp_multiplier_t2", sa.Numeric),
        sa.column("atr_tp_multiplier_t3", sa.Numeric),
    )
    conn = op.get_bind()
    for row in _NEW_STRATEGIES:
        exists = conn.execute(
            sa.text(
                "SELECT 1 FROM strategy_settings WHERE strategy_type = :st LIMIT 1",
            ),
            {"st": row["strategy_type"]},
        ).fetchone()
        if exists is None:
            op.bulk_insert(strategy_settings, [row])


def downgrade() -> None:
    conn = op.get_bind()
    for row in _NEW_STRATEGIES:
        conn.execute(
            sa.text("DELETE FROM strategy_settings WHERE strategy_type = :st"),
            {"st": row["strategy_type"]},
        )
