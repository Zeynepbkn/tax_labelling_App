from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth.security import hash_password, verify_password
from app.config import get_settings
from app.database import SessionLocal
from app.db.models.document import Document, DocumentSplit
from app.db.models.json_upload import JsonUpload
from app.db.models.labeling import LabelingRecord
from app.db.models.quiz import QuizOption, QuizQuestion
from app.db.models.user import User, UserRole


def ensure_initial_admin() -> None:
    """
    Uygulama ilk açıldığında admin yoksa env ile admin oluşturur.
    """
    settings = get_settings()
    if not (settings.admin_username and settings.admin_email and settings.admin_password):
        return

    with SessionLocal() as db:
        admin = db.execute(
            select(User).where(
                User.role == UserRole.admin,
                func.lower(User.email) == settings.admin_email.strip().lower(),
            )
        ).scalar_one_or_none()

        if admin:
            changed = False
            normalized_username = settings.admin_username.strip()
            normalized_email = settings.admin_email.strip().lower()
            if admin.kullanici_adi != normalized_username:
                admin.kullanici_adi = normalized_username
                changed = True
            if admin.email != normalized_email:
                admin.email = normalized_email
                changed = True
            if not verify_password(settings.admin_password, admin.hashed_password):
                admin.hashed_password = hash_password(settings.admin_password)
                changed = True
            if not admin.exam_passed:
                admin.exam_passed = True
                admin.exam_passed_at = datetime.now(timezone.utc)
                changed = True
            if changed:
                db.add(admin)
                db.commit()
            return

        exists = db.execute(select(User.id).where(User.role == UserRole.admin)).first()
        if exists:
            return

        admin = User(
            kullanici_adi=settings.admin_username.strip(),
            email=settings.admin_email.strip().lower(),
            hashed_password=hash_password(settings.admin_password),
            role=UserRole.admin,
            exam_passed=True,
            exam_passed_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()


def get_dashboard_stats(db) -> dict:
    today = date.today()

    total_users = db.execute(select(func.count(User.id))).scalar_one()
    passed_users = db.execute(select(func.count(User.id)).where(User.exam_passed.is_(True))).scalar_one()

    training_documents = db.execute(
        select(func.count(Document.id)).where(Document.split == DocumentSplit.training)
    ).scalar_one()
    annotation_documents = db.execute(
        select(func.count(Document.id)).where(Document.split == DocumentSplit.annotation)
    ).scalar_one()

    total_records = db.execute(select(func.count(LabelingRecord.id))).scalar_one()
    today_records = db.execute(
        select(func.count(LabelingRecord.id)).where(func.date(LabelingRecord.created_at) == today)
    ).scalar_one()

    avg_seconds = db.execute(
        select(func.avg(func.extract("epoch", LabelingRecord.belgeyi_tamamlama_suresi)))
        .where(LabelingRecord.belgeyi_tamamlama_suresi.is_not(None))
    ).scalar_one()

    top = db.execute(
        select(User.id, User.kullanici_adi, func.count(LabelingRecord.id).label("cnt"))
        .join(LabelingRecord, LabelingRecord.user_id == User.id)
        .group_by(User.id)
        .order_by(func.count(LabelingRecord.id).desc())
        .limit(10)
    ).all()

    labels_per_doc = (
        select(LabelingRecord.document_id, func.count(LabelingRecord.id).label("label_count"))
        .group_by(LabelingRecord.document_id)
        .subquery()
    )
    avg_labels_per_doc = db.execute(select(func.avg(labels_per_doc.c.label_count))).scalar_one_or_none()

    return {
        "total_users": total_users,
        "passed_users": passed_users,
        "training_documents": training_documents,
        "annotation_documents": annotation_documents,
        "total_labeling_records": total_records,
        "today_labeling_records": today_records,
        "avg_completion_seconds": float(avg_seconds) if avg_seconds is not None else None,
        "top_labelers": [{"user_id": r.id, "kullanici_adi": r.kullanici_adi, "count": int(r.cnt)} for r in top],
        "avg_labels_per_document": float(avg_labels_per_doc) if avg_labels_per_doc is not None else None,
    }


def get_users_with_stats(db: Session) -> list[dict]:
    rows = db.execute(
        select(
            User,
            func.count(LabelingRecord.id).label("completed"),
            func.avg(func.extract("epoch", LabelingRecord.belgeyi_tamamlama_suresi)).label("avg_sec"),
        )
        .outerjoin(LabelingRecord, LabelingRecord.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    ).all()

    out: list[dict] = []
    for user, completed, avg_sec in rows:
        out.append(
            {
                "user": user,
                "completed_documents": int(completed or 0),
                "avg_duration_seconds": float(avg_sec) if avg_sec is not None else None,
            }
        )
    return out


def delete_user(db: Session, user_id: int, current_admin_id: int) -> None:
    if user_id == current_admin_id:
        raise PermissionError("Kendi admin kullanıcınızı silemezsiniz.")

    user = db.get(User, user_id)
    if not user:
        raise ValueError("Kullanıcı bulunamadı.")

    db.delete(user)
    db.commit()


def get_records(
    db: Session,
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[LabelingRecord], int]:
    stmt = select(LabelingRecord)

    if user_id is not None:
        stmt = stmt.where(LabelingRecord.user_id == user_id)
    if evrak_id is not None:
        stmt = stmt.where(Document.evrak_id == evrak_id).join(Document, Document.id == LabelingRecord.document_id)
    if start_date is not None:
        stmt = stmt.where(func.date(LabelingRecord.created_at) >= start_date)
    if end_date is not None:
        stmt = stmt.where(func.date(LabelingRecord.created_at) <= end_date)
    if min_seconds is not None:
        stmt = stmt.where(func.extract("epoch", LabelingRecord.belgeyi_tamamlama_suresi) >= min_seconds)
    if max_seconds is not None:
        stmt = stmt.where(func.extract("epoch", LabelingRecord.belgeyi_tamamlama_suresi) <= max_seconds)

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one())
    stmt = (
        stmt.options(
            joinedload(LabelingRecord.user).load_only(User.id, User.kullanici_adi),
            joinedload(LabelingRecord.document).load_only(Document.id, Document.evrak_id),
        )
        .order_by(LabelingRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return db.execute(stmt).scalars().all(), total


def get_records_by_evrak_id(db: Session, evrak_id: str) -> list[LabelingRecord]:
    stmt = (
        select(LabelingRecord)
        .join(Document, Document.id == LabelingRecord.document_id)
        .where(Document.evrak_id == evrak_id)
        .options(
            selectinload(LabelingRecord.questions),
            joinedload(LabelingRecord.user).load_only(User.id, User.kullanici_adi),
            joinedload(LabelingRecord.document).load_only(Document.id, Document.evrak_id),
        )
        .order_by(LabelingRecord.created_at.desc())
    )
    return db.execute(stmt).scalars().unique().all()


def delete_labeling_record(db: Session, record_id: int) -> None:
    record = db.get(LabelingRecord, record_id)
    if not record:
        raise ValueError("Etiketleme kaydi bulunamadi.")
    db.delete(record)
    db.commit()


def summarize_json_upload(dataset_type: str, data: Any) -> dict:
    if isinstance(data, list):
        items = data
    else:
        items = [data]

    dict_items = [item for item in items if isinstance(item, dict)]
    sample_keys: list[str] = []
    for item in dict_items[:20]:
        for key in item.keys():
            if key not in sample_keys:
                sample_keys.append(str(key))
            if len(sample_keys) >= 20:
                break
        if len(sample_keys) >= 20:
            break

    summary: dict[str, Any] = {
        "kind": "list" if isinstance(data, list) else type(data).__name__,
        "item_count": len(items) if isinstance(data, list) else 1,
        "object_count": len(dict_items),
        "sample_keys": sample_keys,
    }

    if dataset_type == "training":
        question_keys = sorted({str(k) for item in dict_items[:50] for k in item.keys() if str(k).startswith("soru_")})
        summary.update(
            {
                "documents_with_evrak_id": sum(1 for item in dict_items if item.get("evrak_id")),
                "documents_with_text": sum(1 for item in dict_items if item.get("ozelge_metni")),
                "question_fields": question_keys,
            }
        )
    elif dataset_type == "annotation":
        summary.update(
            {
                "documents_with_evrak_oid": sum(1 for item in dict_items if item.get("evrakOid")),
                "documents_with_html_text": sum(1 for item in dict_items if item.get("htmlText")),
                "documents_with_pdf_text": sum(1 for item in dict_items if item.get("pdfText")),
                "metadata_fields": [k for k in sample_keys if k not in {"htmlText", "pdfText"}],
            }
        )

    return summary


def json_upload_to_dict(upload: JsonUpload) -> dict:
    return {
        "id": upload.id,
        "dataset_type": upload.dataset_type,
        "filename": upload.filename,
        "content_type": upload.content_type,
        "file_size_bytes": upload.file_size_bytes,
        "sha256": upload.sha256,
        "total_items": upload.total_items,
        "added": upload.added,
        "skipped": upload.skipped,
        "duplicates": upload.duplicates,
        "warnings_count": upload.warnings_count,
        "summary": upload.summary_json,
        "uploaded_by_user_id": upload.uploaded_by_user_id,
        "uploaded_by_username": upload.uploaded_by.kullanici_adi if upload.uploaded_by else None,
        "created_at": upload.created_at,
    }


def record_json_upload(
    db: Session,
    *,
    dataset_type: str,
    filename: str,
    content_type: str | None,
    file_size_bytes: int,
    sha256: str,
    total_items: int,
    added: int,
    skipped: int,
    duplicates: int,
    warnings: list[str],
    summary: dict,
    uploaded_by_user_id: int | None,
) -> JsonUpload:
    upload = JsonUpload(
        dataset_type=dataset_type,
        filename=filename,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
        sha256=sha256,
        total_items=total_items,
        added=added,
        skipped=skipped,
        duplicates=duplicates,
        warnings_count=len(warnings),
        summary_json=summary,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def list_json_uploads(db: Session) -> list[dict]:
    uploads = db.execute(
        select(JsonUpload)
        .options(joinedload(JsonUpload.uploaded_by))
        .order_by(JsonUpload.created_at.desc(), JsonUpload.id.desc())
    ).scalars().all()
    return [json_upload_to_dict(upload) for upload in uploads]


def find_json_uploads_by_hash(db: Session, sha256: str) -> list[dict]:
    uploads = db.execute(
        select(JsonUpload)
        .where(JsonUpload.sha256 == sha256)
        .options(joinedload(JsonUpload.uploaded_by))
        .order_by(JsonUpload.created_at.desc(), JsonUpload.id.desc())
    ).scalars().all()
    return [json_upload_to_dict(upload) for upload in uploads]


def _normalize_quiz_payload(payload: dict) -> dict:
    allowed = {
        "question_text",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_option",
        "explanation",
        "active",
    }
    clean = {key: value for key, value in payload.items() if key in allowed}
    correct = clean.get("correct_option")
    if isinstance(correct, str):
        clean["correct_option"] = QuizOption(correct.upper())
    return clean


def create_quiz_question(db: Session, payload: dict) -> QuizQuestion:
    q = QuizQuestion(**_normalize_quiz_payload(payload))
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def update_quiz_question(db: Session, qid: int, payload: dict) -> QuizQuestion:
    q = db.get(QuizQuestion, qid)
    if not q:
        raise ValueError("Quiz sorusu bulunamadı.")
    for k, v in _normalize_quiz_payload(payload).items():
        setattr(q, k, v)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def delete_quiz_question(db: Session, qid: int) -> None:
    q = db.get(QuizQuestion, qid)
    if not q:
        return
    db.delete(q)
    db.commit()


