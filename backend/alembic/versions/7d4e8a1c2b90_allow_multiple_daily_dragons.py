"""allow multiple daily dragon rewards

Revision ID: 7d4e8a1c2b90
Revises: 2c6d8f1a9b30
Create Date: 2026-06-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "7d4e8a1c2b90"
down_revision = "2c6d8f1a9b30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dragon_rewards",
        sa.Column("milestone", sa.Integer(), server_default="0", nullable=False),
    )
    op.drop_constraint("uq_dragon_rewards_user_reward_date", "dragon_rewards", type_="unique")
    # The earliest reward is the quiz reward (milestone 0). Under the old
    # one-reward-per-day rule, later rewards represented the first daily
    # 25-document milestone.
    op.execute(
        sa.text(
            """
            WITH ranked_rewards AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id
                        ORDER BY reward_date, id
                    ) AS reward_number
                FROM dragon_rewards
            )
            UPDATE dragon_rewards AS reward
            SET milestone = 1
            FROM ranked_rewards AS ranked
            WHERE reward.id = ranked.id
              AND ranked.reward_number > 1
            """
        )
    )
    op.create_unique_constraint(
        "uq_dragon_rewards_user_date_milestone",
        "dragon_rewards",
        ["user_id", "reward_date", "milestone"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_dragon_rewards_user_date_milestone", "dragon_rewards", type_="unique")
    # The former schema can retain only one reward for each user and day.
    op.execute(
        sa.text(
            """
            WITH ranked_rewards AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id, reward_date
                        ORDER BY milestone, id
                    ) AS reward_number
                FROM dragon_rewards
            )
            DELETE FROM dragon_rewards AS reward
            USING ranked_rewards AS ranked
            WHERE reward.id = ranked.id
              AND ranked.reward_number > 1
            """
        )
    )
    op.create_unique_constraint(
        "uq_dragon_rewards_user_reward_date",
        "dragon_rewards",
        ["user_id", "reward_date"],
    )
    op.drop_column("dragon_rewards", "milestone")
