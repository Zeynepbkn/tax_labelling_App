from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from app.db.models.document import Document


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LABELLED_QUESTIONS_PATH = PROJECT_ROOT / "labelled_questions.json"
MIN_QUESTION_COLUMNS = 7


def _normalize_text(text: str) -> str:
    if not text:
        return ""

    # Satır sonlarını tek formata indir
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Satır sonlarındaki boşlukları temizle
    lines = [ln.rstrip() for ln in text.split("\n")]

    # Baştaki/sondaki tamamen boş satırları at
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    # Satır başındaki gereksiz indentleri al ve çoklu boş satırı tek satıra indir
    out: list[str] = []
    blank_run = 0
    for ln in lines:
        if not ln.strip():
            blank_run += 1
            if blank_run <= 1:
                out.append("")
        else:
            blank_run = 0
            out.append(ln.lstrip())

    return "\n".join(out)


def _read_labelled_questions(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} okunamadi: JSON formati bozuk.") from exc

    if not isinstance(data, list):
        raise ValueError(f"{path.name} bir JSON listesi olmalidir.")

    return [item for item in data if isinstance(item, dict)]


def _write_labelled_questions(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as temp_file:
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def build_labelled_questions_entry(document: Document, questions: list[str]) -> dict[str, Any]:
    clean_questions = [str(q).strip() for q in questions if q and str(q).strip()]
    column_count = max(MIN_QUESTION_COLUMNS, len(clean_questions))

    raw_text = document.display_text or document.ozelge_metni or ""

    entry: dict[str, Any] = {
        "evrak_id": document.evrak_id,
        "ozelge_metni": _normalize_text(raw_text),
    }
    for idx in range(1, column_count + 1):
        entry[f"soru_{idx}"] = clean_questions[idx - 1] if idx <= len(clean_questions) else None
    entry["soru_sayisi"] = len(clean_questions)
    return entry


def upsert_labelled_questions_entry(
    document: Document,
    questions: list[str],
    path: Path = LABELLED_QUESTIONS_PATH,
) -> None:
    data = _read_labelled_questions(path)
    entry = build_labelled_questions_entry(document, questions)
    evrak_id = str(document.evrak_id)

    for idx, item in enumerate(data):
        if str(item.get("evrak_id")) == evrak_id:
            data[idx] = entry
            break
    else:
        data.append(entry)

    _write_labelled_questions(path, data)
