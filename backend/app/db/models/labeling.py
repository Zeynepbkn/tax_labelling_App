from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    Interval,
    Text,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LabelingRecord(Base):
    __tablename__ = "labeling_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Gerçek etiketlemede cevap zorunlu: boş geçilemez.
    cevap: Mapped[str] = mapped_column(Text, nullable=False)

    doldurulan_soru_kutucugu_sayisi: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # PostgreSQL'de INTERVAL tipine uygundur (örn: 00:05:32)
    belgeyi_tamamlama_suresi: Mapped[object | None] = mapped_column(Interval, nullable=True)
    belge_tamamlama_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="labeling_records")
    document = relationship("Document", back_populates="labeling_records")
    questions = relationship(
        "LabelingQuestion",
        back_populates="labeling_record",
        cascade="all, delete-orphan",
        order_by="LabelingQuestion.question_order",
    )

    __table_args__ = (
        # Aynı kullanıcı aynı belgeyi sadece bir kez labellayabilsin
        Index("uq_labeling_records_user_document", "user_id", "document_id", unique=True),
        CheckConstraint("char_length(btrim(cevap)) > 0", name="labeling_answer_not_empty"),
        CheckConstraint("doldurulan_soru_kutucugu_sayisi >= 0", name="filled_questions_non_negative"),
        Index("ix_labeling_records_document_user", "document_id", "user_id"),
    )


class LabelingQuestion(Base):
    __tablename__ = "labeling_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    labeling_record_id: Mapped[int] = mapped_column(
        ForeignKey("labeling_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # question_text üzerinden otomatik türetilen alan (PostgreSQL generated column)
    character_count: Mapped[int] = mapped_column(
        Integer,
        Computed("char_length(question_text)", persisted=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    labeling_record = relationship("LabelingRecord", back_populates="questions")

    __table_args__ = (
        CheckConstraint("question_order >= 1", name="labeling_question_order_positive"),
        Index("ix_labeling_questions_record_order", "labeling_record_id", "question_order", unique=True),
    )

