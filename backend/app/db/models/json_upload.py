from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JsonUpload(Base):
    __tablename__ = "json_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    added: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    warnings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    uploaded_by = relationship("User", back_populates="json_uploads")

    __table_args__ = (
        Index("ix_json_uploads_dataset_created", "dataset_type", "created_at"),
        Index("ix_json_uploads_filename_size", "filename", "file_size_bytes"),
    )
