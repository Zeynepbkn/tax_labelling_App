from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.db.models.document import DocumentSplit, DisplaySource


class DocumentOut(BaseModel):
    id: int
    evrak_id: str
    display_text: str
    display_source: DisplaySource
    konu: str | None = None
    tarih: str | None = None
    basvuru_tarihi: str | None = None
    vergi_turu: str | None = None
    vergi_donemi: str | None = None
    split: DocumentSplit
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NextDocumentOut(BaseModel):
    document_id: int
    evrak_id: str
    display_text: str
    display_source: DisplaySource
    konu: str | None = None
    tarih: str | None = None
    basvuru_tarihi: str | None = None
    vergi_turu: str | None = None
    vergi_donemi: str | None = None

