"""add quiz attempt details

Revision ID: 2c6d8f1a9b30
Revises: f9a2c7d1e5b6
Create Date: 2026-05-11 19:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "2c6d8f1a9b30"
down_revision = "f9a2c7d1e5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quiz_attempts", sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("quiz_attempts", "details_json")
