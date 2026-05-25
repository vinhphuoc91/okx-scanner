"""Add strategy_settings and system_config tables.

Revision ID: 004
Revises: 003
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_sensitivity_enum = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    name="strategy_sensitivity_enum",
    create_type=False,
)

_DEFAULTS: list[dict] = [
    {
        "strategy_type": "FUNDING",
        "is_enabled": True,
        "min_score": 70,
        "max_concurrent": 3,
        "cooldown_hours": 2.0,
        "sensitivity": "MEDIUM",
        "tp_tier1": 2.0,
        "tp_tier2": 3.0,
        "tp_tier3": 4.0,
        "sl_tier1": 1.0,
        "sl_tier2": 1.5,
        "sl_tier3": 2.0,
        "timeout_tier1": 8,
        "timeout_tier2": 12,
        "timeout_tier3": 24,
    },
    {
        "strategy_type": "MOMENTUM",
        "is_enabled": True,
        "min_score": 75,
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
    },
    {
        "strategy_type": "BREAKOUT",
        "is_enabled": True,
        "min_score": 78,
        "max_concurrent": 2,
        "cooldown_hours": 4.0,
        "sensitivity": "LOW",
        "tp_tier1": 4.0,
        "tp_tier2": 6.0,
        "tp_tier3": 8.0,
        "sl_tier1": 2.0,
        "sl_tier2": 3.0,
        "sl_tier3": 4.0,
        "timeout_tier1": 6,
        "timeout_tier2": 12,
        "timeout_tier3": 24,
    },
    {
        "strategy_type": "VOLUME_ANOMALY",
        "is_enabled": True,
        "min_score": 72,
        "max_concurrent": 2,
        "cooldown_hours": 1.0,
        "sensitivity": "HIGH",
        "tp_tier1": 3.0,
        "tp_tier2": 5.0,
        "tp_tier3": 7.0,
        "sl_tier1": 1.5,
        "sl_tier2": 2.5,
        "sl_tier3": 3.5,
        "timeout_tier1": 4,
        "timeout_tier2": 8,
        "timeout_tier3": 12,
    },
    {
        "strategy_type": "TREND_PULLBACK",
        "is_enabled": True,
        "min_score": 75,
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
    },
]


def upgrade() -> None:
    _sensitivity_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "strategy_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("strategy_type", sa.String(length=64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("min_score", sa.Integer(), nullable=False),
        sa.Column("max_concurrent", sa.Integer(), nullable=False),
        sa.Column("cooldown_hours", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("sensitivity", _sensitivity_enum, nullable=False),
        sa.Column("tp_tier1", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("tp_tier2", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("tp_tier3", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("sl_tier1", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("sl_tier2", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("sl_tier3", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("timeout_tier1", sa.Integer(), nullable=False),
        sa.Column("timeout_tier2", sa.Integer(), nullable=False),
        sa.Column("timeout_tier3", sa.Integer(), nullable=False),
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
        sa.UniqueConstraint("strategy_type", name="uq_strategy_settings_strategy_type"),
        sa.CheckConstraint("min_score >= 50 AND min_score <= 95", name="ck_strategy_settings_min_score"),
        sa.CheckConstraint("max_concurrent >= 1 AND max_concurrent <= 10", name="ck_strategy_settings_max_concurrent"),
        sa.CheckConstraint("cooldown_hours >= 0.5 AND cooldown_hours <= 24", name="ck_strategy_settings_cooldown"),
        sa.CheckConstraint("tp_tier1 > sl_tier1", name="ck_strategy_settings_tp_sl_t1"),
        sa.CheckConstraint("tp_tier2 > sl_tier2", name="ck_strategy_settings_tp_sl_t2"),
        sa.CheckConstraint("tp_tier3 > sl_tier3", name="ck_strategy_settings_tp_sl_t3"),
    )

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
    )
    op.bulk_insert(strategy_settings, _DEFAULTS)

    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_total_concurrent_trades", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("alert_min_score", sa.Integer(), nullable=False, server_default="65"),
        sa.Column("auto_refresh_interval_seconds", sa.Integer(), nullable=False, server_default="10"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="ck_system_config_singleton"),
        sa.CheckConstraint(
            "max_total_concurrent_trades >= 5 AND max_total_concurrent_trades <= 50",
            name="ck_system_config_max_concurrent",
        ),
        sa.CheckConstraint(
            "alert_min_score >= 50 AND alert_min_score <= 95",
            name="ck_system_config_alert_min_score",
        ),
    )
    op.execute(
        sa.text(
            "INSERT INTO system_config (id, max_total_concurrent_trades, alert_min_score, "
            "auto_refresh_interval_seconds) VALUES (1, 5, 65, 10)",
        ),
    )


def downgrade() -> None:
    op.drop_table("system_config")
    op.drop_table("strategy_settings")
    _sensitivity_enum.drop(op.get_bind(), checkfirst=True)
