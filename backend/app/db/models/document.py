from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentSplit(str, enum.Enum):
    training = "training"
    annotation = "annotation"


class DisplaySource(str, enum.Enum):
    htmlText = "htmlText"
    pdfText = "pdfText"
    normalized = "normalized"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Ham veri kaynağındaki `evrakOid` -> burada `evrak_id`
    evrak_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Ham kaynak metinler (korunur)
    pdf_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Kullanıcıya gösterilecek metin (seçilen/temizlenmiş)
    display_text: Mapped[str] = mapped_column(Text, nullable=False)
    display_source: Mapped[DisplaySource] = mapped_column(
        Enum(DisplaySource, name="display_source", native_enum=False),
        nullable=False,
        default=DisplaySource.normalized,
        server_default=DisplaySource.normalized.value,
    )

    # Eğitim JSON'larında gelen metin için geriye uyum: eski kolon adı
    ozelge_metni: Mapped[str] = mapped_column(Text, nullable=False)

    konu: Mapped[str | None] = mapped_column(Text, nullable=True)
    tarih: Mapped[str | None] = mapped_column(String(16), nullable=True)
    basvuru_tarihi: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vergi_turu: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vergi_donemi: Mapped[str | None] = mapped_column(String(32), nullable=True)

    raw_metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    split: Mapped[DocumentSplit] = mapped_column(
        Enum(DocumentSplit, name="document_split", native_enum=False),
        nullable=False,
    )

    # Etiketleme kuyruğu/önceliklendirme için deterministik sıralama
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # Etiketleme kuyruğunda eş zamanlı çekişi önlemek için yumuşak rezervasyon.
    # Bir kullanıcı `/documents/next` çağırdığında belge ona kiralanır; kira süresi
    # (RESERVATION_LEASE_MINUTES) dolana ya da belge etiketlenene kadar başka
    # kullanıcıya gösterilmez. Terk edilen belgeler süre dolunca havuza döner.
    reserved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    training_label = relationship("TrainingLabel", back_populates="document", uselist=False)
    labeling_records = relationship("LabelingRecord", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("order_index >= 0", name="order_index_non_negative"),
        Index("ix_documents_split_order", "split", "order_index"),
        Index("ix_documents_display_source", "display_source"),
        Index("ix_documents_reserved_at", "reserved_at"),
    )

