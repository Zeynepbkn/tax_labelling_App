from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, insert, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.document import Document, DocumentSplit, DisplaySource
from app.db.models.labeling import LabelingRecord
from app.db.models.training import TrainingLabel, TrainingLabelQuestion
from app.services.text_normalization_service import choose_display_text, normalize_document_whitespace


logger = logging.getLogger("taxlabeltr.documents")

# Bir kullanıcı `/documents/next` ile belgeyi çektiğinde belge ona kiralanır.
# Kira süresi dolana kadar belge başka kullanıcıya gösterilmez; süre dolarsa
# (kullanıcı belgeyi terk etmişse) belge tekrar havuza döner. Ortalama
# tamamlama süresi birkaç dakika olduğundan 30 dakikalık kira fazlasıyla yeterli.
RESERVATION_LEASE_MINUTES = 30

def import_training_documents(db: Session, items: list[dict[str, Any]]) -> dict:
    start = time.perf_counter()
    added = skipped = duplicates = updated = converted = 0
    warnings: list[str] = []
    logger.info("training import started items=%s", len(items))

    for idx, item in enumerate(items):
        evrak_id = item.get("evrak_id")
        ozelge_metni = item.get("ozelge_metni")
        if not evrak_id or not ozelge_metni:
            skipped += 1
            warnings.append(f"[{idx}] evrak_id veya ozelge_metni eksik.")
            continue

        evrak_id = str(evrak_id)
        ozelge_metni = normalize_document_whitespace(str(ozelge_metni))
        questions = _extract_training_questions(item)

        existing = db.execute(
            select(Document)
            .where(Document.evrak_id == evrak_id)
            .options(selectinload(Document.training_label).selectinload(TrainingLabel.questions))
        ).scalar_one_or_none()
        if existing:
            existing_questions = [
                q.gold_question_text
                for q in sorted(
                    existing.training_label.questions if existing.training_label else [],
                    key=lambda question: question.question_order,
                )
            ]
            was_training = existing.split == DocumentSplit.training
            has_changed = (
                not was_training
                or existing.ozelge_metni != ozelge_metni
                or existing.display_text != ozelge_metni
                or existing_questions != questions
            )
            if not has_changed:
                duplicates += 1
            else:
                existing.split = DocumentSplit.training
                existing.ozelge_metni = ozelge_metni
                existing.display_text = ozelge_metni
                existing.display_source = DisplaySource.normalized
                existing.order_index = idx
                _replace_training_label_questions(db, existing, questions)
                if was_training:
                    updated += 1
                else:
                    converted += 1
        else:
            doc = Document(
                evrak_id=evrak_id,
                split=DocumentSplit.training,
                ozelge_metni=ozelge_metni,
                display_text=ozelge_metni,
                display_source=DisplaySource.normalized,
                order_index=idx,
            )
            db.add(doc)
            db.flush()
            _replace_training_label_questions(db, doc, questions)
            added += 1

        declared = item.get("soru_sayisi")
        if declared is not None and isinstance(declared, int) and declared != len(questions):
            warnings.append(
                f"[{evrak_id}] soru_sayisi={declared} ama null olmayan soru sayısı={len(questions)}."
            )

    db.commit()
    logger.info(
        "training import finished items=%s added=%s updated=%s converted=%s skipped=%s duplicates=%s warnings=%s elapsed_ms=%.1f",
        len(items),
        added,
        updated,
        converted,
        skipped,
        duplicates,
        len(warnings),
        (time.perf_counter() - start) * 1000,
    )
    return {
        "added": added,
        "updated": updated,
        "converted": converted,
        "skipped": skipped,
        "duplicates": duplicates,
        "warnings": warnings,
    }


def _extract_training_questions(item: dict[str, Any]) -> list[str]:
    question_keys = sorted(
        (key for key in item.keys() if str(key).startswith("soru_") and str(key) != "soru_sayisi"),
        key=lambda key: int(str(key).split("_", 1)[1]) if str(key).split("_", 1)[1].isdigit() else 9999,
    )
    questions: list[str] = []
    for key in question_keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            questions.append(str(value).strip())
    return questions


def _replace_training_label_questions(db: Session, document: Document, questions: list[str]) -> TrainingLabel:
    tlabel = document.training_label
    if not tlabel:
        tlabel = TrainingLabel(document_id=document.id, gold_cevap=None, aciklama=None)
        db.add(tlabel)
        db.flush()

    db.execute(delete(TrainingLabelQuestion).where(TrainingLabelQuestion.training_label_id == tlabel.id))
    db.flush()

    for order, question_text in enumerate(questions, start=1):
        db.add(
            TrainingLabelQuestion(
                training_label_id=tlabel.id,
                question_order=order,
                gold_question_text=question_text,
            )
        )
    return tlabel


def sync_admin_label_to_training(db: Session, document: Document, questions: list[str]) -> TrainingLabel:
    """
    Admin tarafindan uretilen label'i egitim setine yansitir.
    Bu fonksiyon etiketleyici kayıtları için çağrılmaz.
    """
    if document.split != DocumentSplit.training:
        document.split = DocumentSplit.training
    if not document.ozelge_metni:
        document.ozelge_metni = document.display_text or ""
    if not document.display_text:
        document.display_text = document.ozelge_metni or ""
    document.display_source = DisplaySource.normalized
    tlabel = _replace_training_label_questions(db, document, questions)
    db.commit()
    return tlabel


def import_annotation_documents(db: Session, items: list[dict[str, Any]]) -> dict:
    start = time.perf_counter()
    added = skipped = duplicates = 0
    warnings: list[str] = []
    logger.info("annotation import started items=%s", len(items))

    evrak_ids = [str(item.get("evrakOid")) for item in items if item.get("evrakOid")]
    existing_ids: set[str] = set()
    for chunk_start in range(0, len(evrak_ids), 1000):
        chunk = evrak_ids[chunk_start : chunk_start + 1000]
        existing_ids.update(db.execute(select(Document.evrak_id).where(Document.evrak_id.in_(chunk))).scalars().all())

    seen_ids: set[str] = set()
    rows: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        evrak_oid = item.get("evrakOid")
        if not evrak_oid:
            skipped += 1
            warnings.append(f"[{idx}] evrakOid eksik.")
            continue

        evrak_id = str(evrak_oid)
        if evrak_id in existing_ids or evrak_id in seen_ids:
            duplicates += 1
            continue
        seen_ids.add(evrak_id)

        pdf_text = item.get("pdfText")
        html_text = item.get("htmlText")

        display_text, source = choose_display_text(html_text, pdf_text)
        if not display_text:
            # yine de kayıt alalım ama uyarı
            warnings.append(f"[{evrak_oid}] pdfText/htmlText boş görünüyor; display_text boş kaydedildi.")

        raw_metadata = dict(item)
        # büyük metin alanlarını ayrıca kolonlarda tuttuğumuz için metadata'dan çıkar
        raw_metadata.pop("pdfText", None)
        raw_metadata.pop("htmlText", None)

        rows.append(
            {
                "evrak_id": evrak_id,
                "split": DocumentSplit.annotation.value,
                "pdf_text": None,
                "html_text": None,
                "display_text": display_text or "",
                "display_source": DisplaySource(source).value,
                "ozelge_metni": "",
                "konu": item.get("konu"),
                "tarih": item.get("tarih"),
                "basvuru_tarihi": item.get("basvuruTarihi"),
                "vergi_turu": item.get("vergiTuru"),
                "vergi_donemi": item.get("vergiDonemi"),
                "raw_metadata_json": raw_metadata,
                "order_index": idx,
            }
        )
        added += 1

        if len(rows) >= 500:
            db.execute(insert(Document), rows)
            db.commit()
            logger.info("annotation import batch committed batch_size=%s added_so_far=%s", len(rows), added)
            rows.clear()

    if rows:
        db.execute(insert(Document), rows)
        db.commit()
        logger.info("annotation import final batch committed batch_size=%s added_total=%s", len(rows), added)
    logger.info(
        "annotation import finished items=%s added=%s skipped=%s duplicates=%s warnings=%s elapsed_ms=%.1f",
        len(items),
        added,
        skipped,
        duplicates,
        len(warnings),
        (time.perf_counter() - start) * 1000,
    )
    return {"added": added, "skipped": skipped, "duplicates": duplicates, "warnings": warnings}


def select_next_document_for_user(db: Session, user_id: int) -> Document | None:
    """Sıradaki etiketlenecek belgeyi seçer ve kullanıcıya atomik olarak kiralar.

    Önceki sürümde belge yalnızca "henüz etiketlenmiş mi" filtresine göre
    seçiliyordu; bir belge ancak etiketleme *kaydı oluştuğunda* kuyruktan
    düşüyordu. Etiketleme birkaç dakika sürdüğü için bu süre boyunca aynı
    (kuyruğun en üstündeki) belge tüm kullanıcılara dağıtılıyor ve birden çok
    kez etiketleniyordu. Artık belge çekildiği anda kiralanır; kira süresi
    dolana veya etiketlenene kadar başka kullanıcıya gösterilmez.
    """
    now = datetime.now(timezone.utc)
    lease_cutoff = now - timedelta(minutes=RESERVATION_LEASE_MINUTES)

    # Bir belge için herhangi bir etiketleme kaydı varsa belge kuyruktan düşer.
    labeled_exists = select(LabelingRecord.id).where(LabelingRecord.document_id == Document.id).exists()

    # 1) Kullanıcının hâlâ açık (etiketlenmemiş, kirası geçerli) bir rezervasyonu
    #    varsa onu döndür; sayfa yenilendiğinde aynı belge devam etsin.
    own_reserved = db.execute(
        select(Document)
        .where(Document.split == DocumentSplit.annotation)
        .where(~labeled_exists)
        .where(Document.reserved_by_user_id == user_id)
        .where(Document.reserved_at.is_not(None))
        .where(Document.reserved_at >= lease_cutoff)
        .order_by(Document.evrak_id.desc(), Document.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if own_reserved is not None:
        own_reserved.reserved_at = now  # kira süresini tazele
        db.commit()
        return own_reserved

    # 2) Aksi halde boşta olan ya da kirası dolmuş ilk belgeyi atomik olarak kapat.
    #    FOR UPDATE SKIP LOCKED, eş zamanlı isteklerin aynı satırı kapmasını önler:
    #    ikinci istek kilitli satırı atlayıp bir sonrakini alır.
    stmt = (
        select(Document)
        .where(Document.split == DocumentSplit.annotation)
        .where(~labeled_exists)
        .where(
            or_(
                Document.reserved_at.is_(None),
                Document.reserved_at < lease_cutoff,
            )
        )
        .order_by(Document.evrak_id.desc(), Document.id.desc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    doc = db.execute(stmt).scalar_one_or_none()
    if doc is not None:
        doc.reserved_by_user_id = user_id
        doc.reserved_at = now
        db.commit()
    return doc


def get_document_by_evrak_id(db: Session, evrak_id: str) -> Document:
    doc = db.execute(select(Document).where(Document.evrak_id == evrak_id)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Belge bulunamadı.")
    return doc

