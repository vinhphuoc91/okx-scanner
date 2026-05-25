"""Add paper_trades table for performance tracking.

Revision ID: 003
Revises: 002
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_paper_trade_status = postgresql.ENUM(
    "RUNNING",
    "WIN",
    "LOSS",
    "EXPIRED",
    "CANCELLED",
    name="paper_trade_status_enum",
    create_type=False,
)


def upgrade() -> None:
    _paper_trade_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "paper_trades",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("strategy_type", sa.String(length=64), nullable=False),
        sa.Column(
            "direction",
            postgresql.ENUM("LONG", "SHORT", name="opportunity_side_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("entry_price", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("tp_price", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("sl_price", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("tp_pct", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("sl_pct", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("timeout_hours", sa.Integer(), nullable=False),
        sa.Column("status", _paper_trade_status, nullable=False, server_default="RUNNING"),
        sa.Column("entry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("pnl_pct", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", name="uq_paper_trades_opportunity_id"),
    )
    op.create_index("ix_paper_trades_status", "paper_trades", ["status"])
    op.create_index("ix_paper_trades_symbol", "paper_trades", ["symbol"])
    op.create_index("ix_paper_trades_strategy_type", "paper_trades", ["strategy_type"])
    op.create_index("ix_paper_trades_tier", "paper_trades", ["tier"])
    op.create_index("ix_paper_trades_entry_at", "paper_trades", ["entry_at"])


def downgrade() -> None:
    op.drop_index("ix_paper_trades_entry_at", table_name="paper_trades")
    op.drop_index("ix_paper_trades_tier", table_name="paper_trades")
    op.drop_index("ix_paper_trades_strategy_type", table_name="paper_trades")
    op.drop_index("ix_paper_trades_symbol", table_name="paper_trades")
    op.drop_index("ix_paper_trades_status", table_name="paper_trades")
    op.drop_table("paper_trades")
