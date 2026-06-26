from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_exam_passed
from app.database import get_db
from app.db.models.labeling import LabelingRecord
from app.db.models.user import UserRole
from app.schemas.document import DocumentOut, NextDocumentOut
from app.services.document_service import get_document_by_evrak_id, select_next_document_for_user


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/next", response_model=NextDocumentOut)
def next_document(
    db: Session = Depends(get_db),
    current_user=Depends(require_exam_passed),
) -> NextDocumentOut:
    doc = select_next_document_for_user(db, current_user.id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uygun belge bulunamadı.")
    return NextDocumentOut(
        document_id=doc.id,
        evrak_id=doc.evrak_id,
        display_text=doc.display_text,
        display_source=doc.display_source,
        konu=doc.konu,
        tarih=doc.tarih,
        basvuru_tarihi=doc.basvuru_tarihi,
        vergi_turu=doc.vergi_turu,
        vergi_donemi=doc.vergi_donemi,
    )


@router.get("/{evrak_id}", response_model=DocumentOut)
def get_document(
    evrak_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DocumentOut:
    doc = get_document_by_evrak_id(db, evrak_id)
    if current_user.role == UserRole.admin:
        return DocumentOut.model_validate(doc)

    # normal kullanıcı: sadece kendi daha önce labelladığı belgeyi görebilsin
    labeled = db.execute(
        select(LabelingRecord.id).where(LabelingRecord.user_id == current_user.id, LabelingRecord.document_id == doc.id)
    ).first()
    if not labeled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu belgeyi görüntüleme yetkiniz yok.")
    return DocumentOut.model_validate(doc)

