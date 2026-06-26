from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrainingLabel(Base):
    __tablename__ = "training_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Her zaman elde "gold cevap" olmayabilir; eğitim setinde opsiyonel tutulur.
    gold_cevap: Mapped[str | None] = mapped_column(Text, nullable=True)
    aciklama: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    document = relationship("Document", back_populates="training_label")
    questions = relationship(
        "TrainingLabelQuestion",
        back_populates="training_label",
        cascade="all, delete-orphan",
        order_by="TrainingLabelQuestion.question_order",
    )

    __table_args__ = (
        Index("ix_training_labels_document_id", "document_id"),
    )


class TrainingLabelQuestion(Base):
    __tablename__ = "training_label_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_label_id: Mapped[int] = mapped_column(
        ForeignKey("training_labels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    gold_question_text: Mapped[str] = mapped_column(Text, nullable=False)

    training_label = relationship("TrainingLabel", back_populates="questions")

    __table_args__ = (
        CheckConstraint("question_order >= 1", name="training_question_order_positive"),
        Index("ix_training_label_questions_label_order", "training_label_id", "question_order", unique=True),
    )

