"""add json uploads

Revision ID: b3c9a7d2e1f4
Revises: 5374c083e2de
Create Date: 2026-05-09 18:10:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b3c9a7d2e1f4"
down_revision = "5374c083e2de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "json_uploads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_type", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("total_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("added", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("warnings_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_json_uploads_uploaded_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_json_uploads")),
    )
    op.create_index("ix_json_uploads_dataset_created", "json_uploads", ["dataset_type", "created_at"], unique=False)
    op.create_index("ix_json_uploads_filename_size", "json_uploads", ["filename", "file_size_bytes"], unique=False)
    op.create_index(op.f("ix_json_uploads_sha256"), "json_uploads", ["sha256"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_json_uploads_sha256"), table_name="json_uploads")
    op.drop_index("ix_json_uploads_filename_size", table_name="json_uploads")
    op.drop_index("ix_json_uploads_dataset_created", table_name="json_uploads")
    op.drop_table("json_uploads")
