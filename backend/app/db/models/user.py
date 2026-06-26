from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Integer, String, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    labeler = "labeler"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kullanici_adi: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.labeler,
        server_default=UserRole.labeler.value,
    )

    exam_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    exam_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exam_passed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    labeling_records = relationship("LabelingRecord", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    json_uploads = relationship("JsonUpload", back_populates="uploaded_by")
    dragon_rewards = relationship("DragonReward", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "(exam_score IS NULL) OR (exam_score >= 0 AND exam_score <= 100)",
            name="exam_score_range",
        ),
        CheckConstraint(
            "(exam_passed = false) OR (exam_passed_at IS NOT NULL)",
            name="exam_passed_requires_timestamp",
        ),
        Index("ix_users_role", "role"),
    )

