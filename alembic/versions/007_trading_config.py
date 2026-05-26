"""Add trading_config table and real_trading_enabled flag.

Revision ID: 007
Revises: 006
Create Date: 2026-05-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trading_config",
        sa.Column("id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("mode", sa.String(length=10), nullable=False, server_default="paper"),
        sa.Column("api_key", sa.String(length=256), nullable=True),
        sa.Column("api_secret", sa.String(length=256), nullable=True),
        sa.Column("api_passphrase", sa.String(length=256), nullable=True),
        sa.Column("daily_loss_limit_pct", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("size_pct_tier1", sa.Float(), nullable=False, server_default="3.0"),
        sa.Column("size_pct_tier2", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("size_pct_tier3", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("max_leverage", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO trading_config (id, mode, daily_loss_limit_pct, size_pct_tier1, "
            "size_pct_tier2, size_pct_tier3, max_leverage) "
            "VALUES (1, 'paper', 5.0, 3.0, 2.0, 1.0, 5)",
        ),
    )

    op.add_column(
        "strategy_settings",
        sa.Column(
            "real_trading_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column("strategy_settings", "real_trading_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("strategy_settings", "real_trading_enabled")
    op.drop_table("trading_config")
