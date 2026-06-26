"""add document reservation columns

Belgeyi etiketleme kuyruğunda eş zamanlı çekişten kaynaklanan çoğul
etiketlemeyi önlemek için belgelere yumuşak rezervasyon alanları ekler.

Revision ID: c4e1f7a93d22
Revises: 7d4e8a1c2b90
Create Date: 2026-06-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c4e1f7a93d22"
down_revision = "7d4e8a1c2b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("reserved_by_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_documents_reserved_by_user_id_users",
        "documents",
        "users",
        ["reserved_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_documents_reserved_at", "documents", ["reserved_at"])


def downgrade() -> None:
    op.drop_index("ix_documents_reserved_at", table_name="documents")
    op.drop_constraint("fk_documents_reserved_by_user_id_users", "documents", type_="foreignkey")
    op.drop_column("documents", "reserved_at")
    op.drop_column("documents", "reserved_by_user_id")
