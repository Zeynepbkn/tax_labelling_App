from __future__ import annotations

import io
import csv
import json
import zipfile
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models.activity_log import ActivityLog
from app.db.models.document import Document
from app.db.models.dragon_reward import DragonReward
from app.db.models.json_upload import JsonUpload
from app.db.models.labeling import LabelingQuestion, LabelingRecord
from app.db.models.quiz import QuizAttempt, QuizQuestion
from app.db.models.training import TrainingLabel, TrainingLabelQuestion
from app.db.models.user import User

EXPORT_BATCH_SIZE = 500


def _seconds_from_interval(interval) -> int | None:
    if interval is None:
        return None
    try:
        return int(interval.total_seconds())
    except Exception:
        return None


def pivot_questions_to_columns(rows: list[dict]) -> pd.DataFrame:
    # max soru sayısını bul
    max_q = 0
    for r in rows:
        max_q = max(max_q, len(r["questions"]))

    out_rows = []
    for r in rows:
        base = {
            "kullanici_id": r["kullanici_id"],
            "kullanici_adi": r["kullanici_adi"],
            "evrak_id": r["evrak_id"],
            "ozelge_metni": r["ozelge_metni"],
            "doldurulan_soru_kutucugu_sayisi": r["doldurulan_soru_kutucugu_sayisi"],
            "cevap": r["cevap"],
            "belgeyi_tamamlama_suresi": r["belgeyi_tamamlama_suresi"],
            "belge_tamamlama_tarihi": r["belge_tamamlama_tarihi"],
        }
        qs = r["questions"]
        for i in range(1, max_q + 1):
            base[f"soru_{i}"] = qs[i - 1] if i <= len(qs) else None
        out_rows.append(base)
    return pd.DataFrame(out_rows)


def fetch_export_rows(db: Session) -> list[dict]:
    stmt = (
        select(LabelingRecord)
        .options(joinedload(LabelingRecord.questions), joinedload(LabelingRecord.document), joinedload(LabelingRecord.user))
        .order_by(LabelingRecord.created_at.asc())
    )
    records = db.execute(stmt).unique().scalars().all()
    rows: list[dict] = []
    for r in records:
        rows.append(
            {
                "kullanici_id": r.user_id,
                "kullanici_adi": r.user.kullanici_adi if r.user else None,
                "evrak_id": r.document.evrak_id if r.document else None,
                "ozelge_metni": r.document.display_text if r.document else None,
                "doldurulan_soru_kutucugu_sayisi": r.doldurulan_soru_kutucugu_sayisi,
                "questions": [q.question_text for q in sorted(r.questions, key=lambda x: x.question_order)],
                "cevap": r.cevap,
                "belgeyi_tamamlama_suresi": _seconds_from_interval(r.belgeyi_tamamlama_suresi),
                "belge_tamamlama_tarihi": r.belge_tamamlama_tarihi,
            }
        )
    return rows


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "total_seconds"):
        try:
            return int(value.total_seconds())
        except Exception:
            return str(value)
    return value


def _dumps_indented_array_item(value: Any, array_indent: int = 2) -> bytes:
    indent = " " * array_indent
    formatted = json.dumps(value, ensure_ascii=False, indent=2)
    return "\n".join(f"{indent}{line}" for line in formatted.splitlines()).encode("utf-8")


def _records_to_label_export_rows(records: list[LabelingRecord], include_text: bool = False) -> list[dict]:
    rows: list[dict] = []
    for record in records:
        questions = [
            q.question_text
            for q in sorted(record.questions, key=lambda item: item.question_order)
        ]
        row = {
            "evrak_id": record.document.evrak_id if record.document else None,
            "kullanici_adi": record.user.kullanici_adi if record.user else None,
            "soru_sayisi": record.doldurulan_soru_kutucugu_sayisi,
            "created_at": _serialize_value(record.created_at),
            "sorular": questions,
            "cevap": record.cevap,
        }
        if include_text:
            row["ozelge_metni"] = record.document.display_text if record.document else None
        rows.append(row)
    return rows


def _label_record_to_export_row(record: LabelingRecord, include_text: bool = False) -> dict:
    questions = [
        q.question_text
        for q in sorted(record.questions, key=lambda item: item.question_order)
    ]
    row = {
        "evrak_id": record.document.evrak_id if record.document else None,
        "kullanici_adi": record.user.kullanici_adi if record.user else None,
        "soru_sayisi": record.doldurulan_soru_kutucugu_sayisi,
        "created_at": _serialize_value(record.created_at),
        "sorular": questions,
        "cevap": record.cevap,
    }
    if include_text:
        row["ozelge_metni"] = record.document.display_text if record.document else None
    return row


def _label_rows_to_csv_dataframe(rows: list[dict], include_text: bool = False) -> pd.DataFrame:
    base_columns = ["evrak_id"]
    if include_text:
        base_columns.append("ozelge_metni")
    base_columns.extend(["kullanici_adi", "soru_sayisi", "created_at"])
    max_q = max((len(row["sorular"]) for row in rows), default=0)
    columns = base_columns + [f"soru_{idx}" for idx in range(1, max_q + 1)] + ["cevap"]
    csv_rows: list[dict] = []
    for row in rows:
        csv_row = {
            "evrak_id": row["evrak_id"],
            "kullanici_adi": row["kullanici_adi"],
            "soru_sayisi": row["soru_sayisi"],
            "created_at": row["created_at"],
            "cevap": row["cevap"],
        }
        if include_text:
            csv_row["ozelge_metni"] = row.get("ozelge_metni")
        for idx in range(1, max_q + 1):
            csv_row[f"soru_{idx}"] = row["sorular"][idx - 1] if idx <= len(row["sorular"]) else None
        csv_rows.append(csv_row)
    return pd.DataFrame(csv_rows, columns=columns)


def _apply_label_export_filters(
    stmt,
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
) -> Any:
    if evrak_id is not None:
        stmt = stmt.join(Document, Document.id == LabelingRecord.document_id)
    if user_id is not None:
        stmt = stmt.where(LabelingRecord.user_id == user_id)
    if evrak_id is not None:
        stmt = stmt.where(Document.evrak_id == evrak_id)
    if start_date is not None:
        stmt = stmt.where(func.date(LabelingRecord.created_at) >= start_date)
    if end_date is not None:
        stmt = stmt.where(func.date(LabelingRecord.created_at) <= end_date)
    if min_seconds is not None:
        stmt = stmt.where(func.extract("epoch", LabelingRecord.belgeyi_tamamlama_suresi) >= min_seconds)
    if max_seconds is not None:
        stmt = stmt.where(func.extract("epoch", LabelingRecord.belgeyi_tamamlama_suresi) <= max_seconds)
    return stmt


def _label_export_stmt(include_text: bool = False):
    document_load = joinedload(LabelingRecord.document).load_only(Document.id, Document.evrak_id)
    if include_text:
        document_load = joinedload(LabelingRecord.document).load_only(
            Document.id,
            Document.evrak_id,
            Document.display_text,
        )

    return select(LabelingRecord).options(
        selectinload(LabelingRecord.questions),
        joinedload(LabelingRecord.user).load_only(User.id, User.kullanici_adi),
        document_load,
    )


def _iter_label_export_records(
    db: Session,
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    include_text: bool = False,
):
    stmt = _apply_label_export_filters(
        _label_export_stmt(include_text=include_text),
        user_id=user_id,
        evrak_id=evrak_id,
        start_date=start_date,
        end_date=end_date,
        min_seconds=min_seconds,
        max_seconds=max_seconds,
    )
    stmt = stmt.order_by(LabelingRecord.created_at.desc()).execution_options(yield_per=EXPORT_BATCH_SIZE)
    yield from db.execute(stmt).scalars()


def fetch_label_export_rows(
    db: Session,
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    include_text: bool = False,
) -> list[dict]:
    records = list(
        _iter_label_export_records(
            db,
            user_id=user_id,
            evrak_id=evrak_id,
            start_date=start_date,
            end_date=end_date,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
            include_text=include_text,
        )
    )
    return _records_to_label_export_rows(records, include_text=include_text)


def iter_labeling_records_json(
    db: Session,
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    include_text: bool = False,
):
    yield b"[\n"
    first = True
    for record in _iter_label_export_records(
        db,
        user_id=user_id,
        evrak_id=evrak_id,
        start_date=start_date,
        end_date=end_date,
        min_seconds=min_seconds,
        max_seconds=max_seconds,
        include_text=include_text,
    ):
        prefix = b"" if first else b",\n"
        first = False
        row = _label_record_to_export_row(record, include_text=include_text)
        yield prefix + _dumps_indented_array_item(row)
    yield b"\n]\n"


def _max_question_count(
    db: Session,
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
) -> int:
    stmt = _apply_label_export_filters(
        select(func.max(LabelingRecord.doldurulan_soru_kutucugu_sayisi)),
        user_id=user_id,
        evrak_id=evrak_id,
        start_date=start_date,
        end_date=end_date,
        min_seconds=min_seconds,
        max_seconds=max_seconds,
    )
    return int(db.execute(stmt).scalar_one_or_none() or 0)


def iter_labeling_records_csv(
    db: Session,
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    include_text: bool = False,
):
    max_q = _max_question_count(db, user_id, evrak_id, start_date, end_date, min_seconds, max_seconds)
    columns = ["evrak_id"]
    if include_text:
        columns.append("ozelge_metni")
    columns.extend(["kullanici_adi", "soru_sayisi", "created_at"])
    columns.extend(f"soru_{idx}" for idx in range(1, max_q + 1))
    columns.append("cevap")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    yield "\ufeff".encode("utf-8")
    writer.writeheader()
    yield buffer.getvalue().encode("utf-8")

    for record in _iter_label_export_records(
        db,
        user_id=user_id,
        evrak_id=evrak_id,
        start_date=start_date,
        end_date=end_date,
        min_seconds=min_seconds,
        max_seconds=max_seconds,
        include_text=include_text,
    ):
        row = _label_record_to_export_row(record, include_text=include_text)
        csv_row = {
            "evrak_id": row["evrak_id"],
            "kullanici_adi": row["kullanici_adi"],
            "soru_sayisi": row["soru_sayisi"],
            "created_at": row["created_at"],
            "cevap": row["cevap"],
        }
        if include_text:
            csv_row["ozelge_metni"] = row.get("ozelge_metni")
        for idx in range(1, max_q + 1):
            csv_row[f"soru_{idx}"] = row["sorular"][idx - 1] if idx <= len(row["sorular"]) else None
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow(csv_row)
        yield buffer.getvalue().encode("utf-8")


def export_labeling_records_to_json(
    db: Session,
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    include_text: bool = False,
) -> bytes:
    rows = fetch_label_export_rows(db, user_id, evrak_id, start_date, end_date, min_seconds, max_seconds, include_text)
    return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")


def export_labeling_records_to_csv(
    db: Session,
    user_id: int | None = None,
    evrak_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
    include_text: bool = False,
) -> bytes:
    rows = fetch_label_export_rows(db, user_id, evrak_id, start_date, end_date, min_seconds, max_seconds, include_text)
    df = _label_rows_to_csv_dataframe(rows, include_text=include_text)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8-sig")


def _table_models() -> list[tuple[str, type]]:
    return [
        ("users", User),
        ("documents", Document),
        ("training_labels", TrainingLabel),
        ("training_label_questions", TrainingLabelQuestion),
        ("labeling_records", LabelingRecord),
        ("labeling_questions", LabelingQuestion),
        ("quiz_questions", QuizQuestion),
        ("quiz_attempts", QuizAttempt),
        ("json_uploads", JsonUpload),
        ("activity_logs", ActivityLog),
        ("dragon_rewards", DragonReward),
    ]


def _model_row_to_dict(row: Any, columns: list[str]) -> dict:
    return {column: _serialize_value(getattr(row, column)) for column in columns}


def _model_rows(db: Session, model: type) -> list[dict]:
    columns = [column.name for column in model.__table__.columns]
    rows = db.execute(select(model).order_by(model.id.asc())).scalars().all()
    return [_model_row_to_dict(row, columns) for row in rows]


def _iter_model_rows(db: Session, model: type):
    columns = [column.name for column in model.__table__.columns]
    stmt = select(model).order_by(model.id.asc()).execution_options(yield_per=EXPORT_BATCH_SIZE)
    for row in db.execute(stmt).scalars():
        yield _model_row_to_dict(row, columns)
        db.expunge(row)


def _write_json_table_member(backup: zipfile.ZipFile, table_name: str, rows) -> None:
    with backup.open(f"tables/{table_name}.json", mode="w", force_zip64=True) as member:
        member.write(b"[\n")
        first = True
        for row in rows:
            prefix = b"" if first else b",\n"
            first = False
            member.write(prefix + _dumps_indented_array_item(row))
        member.write(b"\n]\n")


def write_database_backup_zip(db: Session, output_path: str | Path | io.BytesIO) -> None:
    exported_at = datetime.now().astimezone().isoformat()
    table_models = _table_models()
    table_counts = {
        name: int(db.execute(select(func.count()).select_from(model)).scalar_one())
        for name, model in table_models
    }
    manifest = {
        "exported_at": exported_at,
        "format": "taxlabeltr-table-json-backup-v1",
        "notes": [
            "Bu ZIP uygulama tablolarini JSON olarak saklar.",
            "Ortam degiskenleri, DATABASE_URL, SECRET_KEY veya .env dosyalari dahil edilmez.",
        ],
        "tables": table_counts,
    }

    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as backup:
        backup.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        for table_name, model in table_models:
            _write_json_table_member(backup, table_name, _iter_model_rows(db, model))


def export_database_backup_zip(db: Session) -> bytes:
    out = io.BytesIO()
    write_database_backup_zip(db, out)
    return out.getvalue()


def export_labeling_records_to_excel(db: Session) -> bytes:
    rows = fetch_export_rows(db)
    df = pivot_questions_to_columns(rows)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="labeling_records", index=False)
    return out.getvalue()


def export_backup_excel(db: Session) -> bytes:
    out = io.BytesIO()

    users = db.execute(select(User)).scalars().all()
    documents = db.execute(select(Document)).scalars().all()
    records = db.execute(select(LabelingRecord).options(joinedload(LabelingRecord.questions))).unique().scalars().all()

    users_df = pd.DataFrame(
        [
            {
                "id": u.id,
                "kullanici_adi": u.kullanici_adi,
                "email": u.email,
                "role": u.role.value,
                "exam_passed": u.exam_passed,
                "exam_score": u.exam_score,
                "exam_passed_at": u.exam_passed_at,
                "created_at": u.created_at,
                "last_login_at": u.last_login_at,
            }
            for u in users
        ]
    )

    docs_df = pd.DataFrame(
        [
            {
                "id": d.id,
                "evrak_id": d.evrak_id,
                "split": d.split.value,
                "display_source": d.display_source.value,
                "konu": d.konu,
                "tarih": d.tarih,
                "basvuru_tarihi": d.basvuru_tarihi,
                "vergi_turu": d.vergi_turu,
                "vergi_donemi": d.vergi_donemi,
                "created_at": d.created_at,
                "updated_at": d.updated_at,
            }
            for d in documents
        ]
    )

    rec_df = pd.DataFrame(
        [
            {
                "id": r.id,
                "user_id": r.user_id,
                "document_id": r.document_id,
                "doldurulan_soru_kutucugu_sayisi": r.doldurulan_soru_kutucugu_sayisi,
                "cevap": r.cevap,
                "belgeyi_tamamlama_suresi_seconds": _seconds_from_interval(r.belgeyi_tamamlama_suresi),
                "belge_tamamlama_tarihi": r.belge_tamamlama_tarihi,
                "created_at": r.created_at,
            }
            for r in records
        ]
    )

    q_df = pd.DataFrame(
        [
            {
                "labeling_record_id": r.id,
                "question_order": q.question_order,
                "question_text": q.question_text,
                "character_count": q.character_count,
                "created_at": q.created_at,
            }
            for r in records
            for q in r.questions
        ]
    )

    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="users", index=False)
        docs_df.to_excel(writer, sheet_name="documents", index=False)
        rec_df.to_excel(writer, sheet_name="labeling_records", index=False)
        q_df.to_excel(writer, sheet_name="labeling_questions", index=False)

    return out.getvalue()

