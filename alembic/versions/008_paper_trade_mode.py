"""Add mode column to paper_trades for paper vs real execution.

Revision ID: 008
Revises: 007
Create Date: 2026-05-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "paper_trades",
        sa.Column("mode", sa.String(length=10), nullable=False, server_default="paper"),
    )
    op.alter_column("paper_trades", "mode", server_default=None)


def downgrade() -> None:
    op.drop_column("paper_trades", "mode")
