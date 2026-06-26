from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_exam_passed
from app.database import get_db
from app.db.models.document import Document
from app.db.models.user import UserRole
from app.schemas.labeling import (
    LeaderboardOut,
    LabelingRecordOut,
    LabelingRecordSummaryOut,
    LabelingSubmitRequest,
    LabelingSubmitResponse,
    LabelingUpdateRequest,
    MyProgressOut,
    PaginatedLabelingRecordSummaryOut,
)
from app.services.labeling_service import (
    create_labeling_record,
    ensure_can_modify_labeling_record,
    fetch_labeling_record_by_id,
    generate_quality_warnings,
    get_leaderboard,
    get_user_progress,
    get_user_records,
    labeling_record_to_out,
    labeling_record_summary_to_out,
    normalize_labeling_inputs,
    update_labeling_record,
    validate_labeling_quality,
    validate_labeling_submission,
)
from app.services.document_service import sync_admin_label_to_training
from app.services.labelled_questions_file_service import upsert_labelled_questions_entry


router = APIRouter(prefix="/labeling", tags=["labeling"])


@router.post("/submit", response_model=LabelingSubmitResponse)
def submit(
    payload: LabelingSubmitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_exam_passed),
) -> LabelingSubmitResponse:
    raw_questions = payload.questions
    raw_cevap = payload.cevap
    questions, cevap = normalize_labeling_inputs(payload.questions, payload.cevap)
    validate_labeling_submission(questions, cevap)

    # Document metnini DB'den al (quality heuristics)
    doc = db.get(Document, payload.document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Belge bulunamadı.")
    validate_labeling_quality(doc.display_text, questions, cevap)

    warnings = generate_quality_warnings(
        document_text=doc.display_text,
        questions=questions,
        cevap=cevap,
        duration_seconds=payload.belgeyi_tamamlama_suresi,
        raw_questions=raw_questions,
        raw_cevap=raw_cevap,
    )
    if warnings and not payload.force_submit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"warnings": warnings})

    rec = create_labeling_record(
        db=db,
        user_id=current_user.id,
        document_id=payload.document_id,
        questions=questions,
        cevap=cevap,
        duration_seconds=payload.belgeyi_tamamlama_suresi,
    )
    if current_user.role == UserRole.admin:
        upsert_labelled_questions_entry(doc, questions)
        sync_admin_label_to_training(db, doc, questions)

    return LabelingSubmitResponse(record_id=rec.id, message="Kayıt başarıyla alındı.", warnings=warnings)


@router.get("/my-progress", response_model=MyProgressOut)
def my_progress(db: Session = Depends(get_db), current_user=Depends(require_exam_passed)) -> MyProgressOut:
    data = get_user_progress(db, current_user.id)
    return MyProgressOut(**data)


@router.get("/leaderboard", response_model=LeaderboardOut)
def leaderboard(db: Session = Depends(get_db), current_user=Depends(require_exam_passed)) -> LeaderboardOut:
    data = get_leaderboard(db, current_user.id)
    return LeaderboardOut(**data)


@router.get("/my-records", response_model=PaginatedLabelingRecordSummaryOut)
def my_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    evrak_id: str | None = Query(None, max_length=64),
    sort: str = Query("newest", pattern="^(newest|question_count_asc)$"),
    db: Session = Depends(get_db),
    current_user=Depends(require_exam_passed),
) -> PaginatedLabelingRecordSummaryOut:
    records, total = get_user_records(
        db,
        current_user.id,
        page=page,
        page_size=page_size,
        evrak_id=evrak_id,
        sort=sort,
    )
    return PaginatedLabelingRecordSummaryOut(
        items=[labeling_record_summary_to_out(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/records/{record_id}", response_model=LabelingRecordOut)
def get_labeling_record(record_id: int, db: Session = Depends(get_db), current_user=Depends(require_exam_passed)) -> LabelingRecordOut:
    rec = fetch_labeling_record_by_id(db, record_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıt bulunamadı.")
    ensure_can_modify_labeling_record(current_user, rec)
    return labeling_record_to_out(rec)


@router.patch("/records/{record_id}", response_model=LabelingSubmitResponse)
def patch_labeling_record(
    record_id: int,
    payload: LabelingUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_exam_passed),
) -> LabelingSubmitResponse:
    raw_questions = payload.questions
    raw_cevap = payload.cevap
    questions, cevap = normalize_labeling_inputs(payload.questions, payload.cevap)
    validate_labeling_submission(questions, cevap)
    rec = fetch_labeling_record_by_id(db, record_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıt bulunamadı.")
    ensure_can_modify_labeling_record(current_user, rec)

    doc = db.get(Document, rec.document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Belge bulunamadı.")
    validate_labeling_quality(doc.display_text, questions, cevap)

    warnings = generate_quality_warnings(
        document_text=doc.display_text,
        questions=questions,
        cevap=cevap,
        duration_seconds=payload.belgeyi_tamamlama_suresi,
        raw_questions=raw_questions,
        raw_cevap=raw_cevap,
    )
    if warnings and not payload.force_submit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"warnings": warnings})

    updated = update_labeling_record(
        db=db,
        record=rec,
        questions=questions,
        cevap=cevap,
        duration_seconds=payload.belgeyi_tamamlama_suresi,
    )
    if current_user.role == UserRole.admin and rec.user_id == current_user.id:
        upsert_labelled_questions_entry(doc, questions)
        sync_admin_label_to_training(db, doc, questions)
    return LabelingSubmitResponse(record_id=updated.id, message="Kayıt güncellendi.", warnings=warnings)

