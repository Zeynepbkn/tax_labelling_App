"""add dragon rewards

Revision ID: f9a2c7d1e5b6
Revises: b3c9a7d2e1f4
Create Date: 2026-05-10 16:30:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f9a2c7d1e5b6"
down_revision = "b3c9a7d2e1f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dragon_rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reward_date", sa.Date(), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_dragon_rewards_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dragon_rewards")),
        sa.UniqueConstraint("user_id", "reward_date", name="uq_dragon_rewards_user_reward_date"),
    )
    op.create_index(op.f("ix_dragon_rewards_user_id"), "dragon_rewards", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dragon_rewards_user_id"), table_name="dragon_rewards")
    op.drop_table("dragon_rewards")
