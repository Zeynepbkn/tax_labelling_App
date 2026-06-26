from __future__ import annotations

import io
import hashlib
import logging
import os
import tempfile
import time

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.auth.dependencies import require_admin
from app.config import get_settings
from app.database import get_db
from app.schemas.admin import DashboardOut, JsonUploadOut, PaginatedAdminRecordsOut, UploadDuplicateCheckOut, UploadResult
from app.schemas.quiz import AdminQuizQuestionOut, QuizQuestionUpsert
from app.schemas.user import AdminUserStatsOut, UserOut
from app.services import admin_service
from app.services.document_service import import_annotation_documents, import_training_documents
from app.services.export_service import (
    export_backup_excel,
    export_labeling_records_to_excel,
    iter_labeling_records_csv,
    iter_labeling_records_json,
    write_database_backup_zip,
)
from app.utils.json_loader import parse_json_bytes, read_upload_bytes


router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger("taxlabeltr.admin")


def _delete_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


@router.post("/upload-training-json", response_model=UploadResult)
async def upload_training_json(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> UploadResult:
    start = time.perf_counter()
    logger.info("training upload started filename=%s content_type=%s", file.filename, file.content_type)
    try:
        content = await read_upload_bytes(file, get_settings().json_upload_max_bytes)
        sha256 = hashlib.sha256(content).hexdigest()
        data = parse_json_bytes(content)
        if not isinstance(data, list):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON bir liste olmalidir.")
        result = import_training_documents(db, data)
        summary = admin_service.summarize_json_upload("training", data)
        upload = admin_service.record_json_upload(
            db,
            dataset_type="training",
            filename=file.filename or "unknown.json",
            content_type=file.content_type,
            file_size_bytes=len(content),
            sha256=sha256,
            total_items=len(data),
            added=result.get("added", 0),
            skipped=result.get("skipped", 0),
            duplicates=result.get("duplicates", 0),
            warnings=result.get("warnings", []),
            summary=summary,
            uploaded_by_user_id=admin.id,
        )
        logger.info(
            "training upload finished filename=%s items=%s added=%s updated=%s converted=%s skipped=%s duplicates=%s elapsed_ms=%.1f",
            file.filename,
            len(data),
            result.get("added"),
            result.get("updated"),
            result.get("converted"),
            result.get("skipped"),
            result.get("duplicates"),
            (time.perf_counter() - start) * 1000,
        )
        return UploadResult(**result, upload=JsonUploadOut(**admin_service.json_upload_to_dict(upload)))
    except HTTPException:
        logger.warning("training upload rejected filename=%s elapsed_ms=%.1f", file.filename, (time.perf_counter() - start) * 1000)
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("training upload failed filename=%s elapsed_ms=%.1f", file.filename, (time.perf_counter() - start) * 1000)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Eğitim JSON yüklenemedi: {exc}")


@router.post("/upload-annotation-json", response_model=UploadResult)
async def upload_annotation_json(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> UploadResult:
    start = time.perf_counter()
    logger.info("annotation upload started filename=%s content_type=%s", file.filename, file.content_type)
    try:
        content = await read_upload_bytes(file, get_settings().json_upload_max_bytes)
        sha256 = hashlib.sha256(content).hexdigest()
        data = parse_json_bytes(content)
        if not isinstance(data, list):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON bir liste olmalidir.")
        result = import_annotation_documents(db, data)
        summary = admin_service.summarize_json_upload("annotation", data)
        upload = admin_service.record_json_upload(
            db,
            dataset_type="annotation",
            filename=file.filename or "unknown.json",
            content_type=file.content_type,
            file_size_bytes=len(content),
            sha256=sha256,
            total_items=len(data),
            added=result.get("added", 0),
            skipped=result.get("skipped", 0),
            duplicates=result.get("duplicates", 0),
            warnings=result.get("warnings", []),
            summary=summary,
            uploaded_by_user_id=admin.id,
        )
        logger.info(
            "annotation upload finished filename=%s items=%s added=%s skipped=%s duplicates=%s elapsed_ms=%.1f",
            file.filename,
            len(data),
            result.get("added"),
            result.get("skipped"),
            result.get("duplicates"),
            (time.perf_counter() - start) * 1000,
        )
        return UploadResult(**result, upload=JsonUploadOut(**admin_service.json_upload_to_dict(upload)))
    except HTTPException:
        logger.warning("annotation upload rejected filename=%s elapsed_ms=%.1f", file.filename, (time.perf_counter() - start) * 1000)
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("annotation upload failed filename=%s elapsed_ms=%.1f", file.filename, (time.perf_counter() - start) * 1000)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Özelge JSON yüklenemedi: {exc}")


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), _admin=Depends(require_admin)) -> DashboardOut:
    stats = admin_service.get_dashboard_stats(db)
    return DashboardOut(**stats)


@router.get("/users", response_model=list[AdminUserStatsOut])
def users(db: Session = Depends(get_db), _admin=Depends(require_admin)) -> list[AdminUserStatsOut]:
    rows = admin_service.get_users_with_stats(db)
    out: list[AdminUserStatsOut] = []
    for r in rows:
        u = r["user"]
        out.append(
            AdminUserStatsOut(
                **UserOut.model_validate(u).model_dump(),
                completed_documents=r["completed_documents"],
                avg_duration_seconds=r["avg_duration_seconds"],
            )
        )
    return out


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    try:
        admin_service.delete_user(db, user_id, admin.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"message": "Kullanıcı silindi."}


@router.get("/uploads", response_model=list[JsonUploadOut])
def list_uploads(db: Session = Depends(get_db), _admin=Depends(require_admin)) -> list[JsonUploadOut]:
    return [JsonUploadOut(**row) for row in admin_service.list_json_uploads(db)]


@router.get("/uploads/check", response_model=UploadDuplicateCheckOut)
def check_upload(
    sha256: str = Query(..., min_length=64, max_length=64),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> UploadDuplicateCheckOut:
    matches = [JsonUploadOut(**row) for row in admin_service.find_json_uploads_by_hash(db, sha256.lower())]
    return UploadDuplicateCheckOut(exists=bool(matches), matches=matches)


@router.get("/records")
def records(
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> PaginatedAdminRecordsOut:
    recs, total = admin_service.get_records(
        db,
        user_id,
        evrak_id,
        start_date,
        end_date,
        min_seconds,
        max_seconds,
        page=page,
        page_size=page_size,
    )
    return PaginatedAdminRecordsOut(
        items=[
            {
                "id": r.id,
                "user_id": r.user_id,
                "kullanici_adi": r.user.kullanici_adi if r.user else None,
                "evrak_id": r.document.evrak_id if r.document else None,
                "soru_sayisi": r.doldurulan_soru_kutucugu_sayisi,
                "cevap": r.cevap,
                "belgeyi_tamamlama_suresi_seconds": int(r.belgeyi_tamamlama_suresi.total_seconds())
                if r.belgeyi_tamamlama_suresi
                else None,
                "belge_tamamlama_tarihi": r.belge_tamamlama_tarihi,
                "created_at": r.created_at,
            }
            for r in recs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/records/{evrak_id}")
def records_by_evrak_id(evrak_id: str, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    recs = admin_service.get_records_by_evrak_id(db, evrak_id)
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "kullanici_adi": r.user.kullanici_adi if r.user else None,
            "evrak_id": r.document.evrak_id if r.document else None,
            "soru_sayisi": r.doldurulan_soru_kutucugu_sayisi,
            "cevap": r.cevap,
            "questions": [{"order": q.question_order, "text": q.question_text} for q in r.questions],
            "created_at": r.created_at,
        }
        for r in recs
    ]


@router.delete("/records/by-id/{record_id}")
def delete_labeling_record(record_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    try:
        admin_service.delete_labeling_record(db, record_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"message": "Etiketleme kaydi silindi."}


@router.get("/export/json")
def export_json(
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    include_text: bool = False,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    filename = "labeling_records_with_text.json" if include_text else "labeling_records.json"
    return StreamingResponse(
        iter_labeling_records_json(
            db,
            user_id=user_id,
            evrak_id=evrak_id,
            start_date=start_date,
            end_date=end_date,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
            include_text=include_text,
        ),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/csv")
def export_csv(
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    include_text: bool = False,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    filename = "labeling_records_with_text.csv" if include_text else "labeling_records.csv"
    return StreamingResponse(
        iter_labeling_records_csv(
            db,
            user_id=user_id,
            evrak_id=evrak_id,
            start_date=start_date,
            end_date=end_date,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
            include_text=include_text,
        ),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/excel")
def export_excel(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    data = export_labeling_records_to_excel(db)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="labeling_records.xlsx"'},
    )


@router.get("/backup")
def backup(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    data = export_backup_excel(db)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="backup.xlsx"'},
    )


@router.get("/backup/zip")
def backup_zip(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    tmp = tempfile.NamedTemporaryFile(prefix="taxlabeltr_database_backup_", suffix=".zip", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        write_database_backup_zip(db, tmp_path)
    except Exception:
        _delete_file(tmp_path)
        raise
    return FileResponse(
        tmp_path,
        media_type="application/zip",
        filename="taxlabeltr_database_backup.zip",
        background=BackgroundTask(_delete_file, tmp_path),
    )


@router.get("/quiz/questions", response_model=list[AdminQuizQuestionOut])
def list_quiz_questions(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    from sqlalchemy import select
    from app.db.models.quiz import QuizQuestion

    qs = db.execute(select(QuizQuestion).order_by(QuizQuestion.id.asc())).scalars().all()
    return [AdminQuizQuestionOut.model_validate(q) for q in qs]


@router.post("/quiz/questions", response_model=AdminQuizQuestionOut)
def create_quiz(payload: QuizQuestionUpsert, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    q = admin_service.create_quiz_question(db, payload.model_dump())
    return AdminQuizQuestionOut.model_validate(q)


@router.put("/quiz/questions/{qid}", response_model=AdminQuizQuestionOut)
def update_quiz(qid: int, payload: QuizQuestionUpsert, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    try:
        q = admin_service.update_quiz_question(db, qid, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AdminQuizQuestionOut.model_validate(q)


@router.delete("/quiz/questions/{qid}")
def delete_quiz(qid: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    admin_service.delete_quiz_question(db, qid)
    return {"message": "Silindi."}
