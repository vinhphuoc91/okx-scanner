"""Add scan tier columns to instruments.

Revision ID: 002
Revises: 001
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("instruments", sa.Column("tier", sa.Integer(), nullable=True))
    op.add_column("instruments", sa.Column("scan_interval_seconds", sa.Integer(), nullable=True))
    op.create_index("ix_instruments_tier", "instruments", ["tier"])


def downgrade() -> None:
    op.drop_index("ix_instruments_tier", table_name="instruments")
    op.drop_column("instruments", "scan_interval_seconds")
    op.drop_column("instruments", "tier")
