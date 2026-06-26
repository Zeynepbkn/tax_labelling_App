from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models.document import Document, DocumentSplit
from app.db.models.dragon_reward import DragonReward
from app.db.models.labeling import LabelingQuestion, LabelingRecord
from app.db.models.user import User, UserRole
from app.schemas.labeling import LabelingQuestionOut, LabelingRecordOut, LabelingRecordSummaryOut


DRAGON_COLORS = ["ruby", "emerald", "sapphire", "amber", "violet", "aqua", "rose", "gold","platinum","silver"]
DRAGON_NAMES = ["Kivilcim", "Poyraz", "Lodos", "Mavi Alev", "Zirve", "Kutup", "Mercan", "Firtina","parıltı","Gök"]
DRAGON_THRESHOLD = 25
LEADERBOARD_COMPLETED_POINTS = 10
LEADERBOARD_TODAY_BONUS_POINTS = 2
LEADERBOARD_DRAGON_POINTS = 100


def _earned_daily_dragon_count(completed_count: int) -> int:
    return max(0, completed_count) // DRAGON_THRESHOLD
MIN_QUESTION_QUALITY_TOKENS = 8
MIN_ANSWER_QUALITY_TOKENS = 40
MIN_QUESTION_DOCUMENT_OVERLAP = 0.35
MIN_ANSWER_DOCUMENT_OVERLAP = 0.40
MIN_VOWEL_RATIO = 0.20
MIN_CONSECUTIVE_REPEATED_TOKENS = 3
MIN_PHRASE_REPETITION_NGRAM = 8
MIN_PHRASE_REPETITION_COUNT = 3
MIN_REPEATED_LETTER_RUN = 7
MIN_REPEATED_DIGIT_RUN = 8
MIN_SOURCE_ZONE_OVERLAP = 0.30
MIN_WRONG_ZONE_OVERLAP = 0.65
MIN_ZONE_OVERLAP_GAP = 0.25
ANSWER_EDGE_TOKEN_WINDOW = 80
MIN_ANSWER_TAIL_OVERLAP = 0.12

TURKISH_STOPWORDS = {
    "acaba",
    "ama",
    "ancak",
    "arada",
    "ayni",
    "bazi",
    "ben",
    "beri",
    "bir",
    "buna",
    "bunda",
    "bundan",
    "bunu",
    "da",
    "daha",
    "de",
    "diye",
    "en",
    "gibi",
    "icin",
    "ile",
    "ise",
    "kadar",
    "mi",
    "mu",
    "ne",
    "olarak",
    "olan",
    "olup",
    "sonra",
    "ve",
    "veya",
    "ya",
}

QUESTION_ENDING_MARKERS = [
    "sorulmaktadır",
    "talep edildiği anlaşılmaktadır",
    "talep edildiği anlaşılmıştır",
    "talep ettiğiniz anlaşılmıştır",
    "talep edilmektedir",
    "görüşü istenilmektedir",
    "görüş istenilmektedir",
    "talep ettiğiniz anlaşılmaktadır",
]

ANSWER_CLOSING_MARKERS = [
    "bilgi edinilmesini rica ederim",
    "bilgi edinilmesini arz ederim",
]

ANSWER_CONCLUSION_MARKERS = [
    "buna gore",
    "bu hukum ve aciklamalara gore",
    "yukarida yer alan hukum ve aciklamalar cercevesinde",
    "cercevesinde",
    "mumkun bulunmamaktadir",
    "mumkun bulunmaktadir",
    "gerekmektedir",
    "gerekmeyecektir",
    "tabi olacaktir",
    "tabi olmayacaktir",
    "tabiidir",
    "vergileme yapilmayacaktir",
    "istisna kapsaminda",
    "indirim konusu yapilabilecektir",
    "hesaplanmasi gerekmektedir",
    "degerlendirilmesi mumkun degildir",
]

SOURCE_QUESTION_ANSWER_BOUNDARY_MARKERS = [
    "sorulmaktadir",
    "talep edildigi anlasilmaktadir",
    "talep edildigi anlasilmistir",
    "talep ettiginiz anlasilmistir",
    "talep edilmektedir",
    "gorusu istenilmektedir",
    "gorus istenilmektedir",
    "anlasilmaktadir",
]

SOURCE_ANSWER_CLOSING_MARKERS = [
    "bilgi edinilmesini rica ederim",
    "bilgi edinilmesini arz ederim",
    "bilgilendirilmesini rica ederim",
    "bilgilendirilmesini arz ederim",
]


def clean_labeling_field_text(value: str | None) -> str:
    lines = str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(re.sub(r"^\s*[-\u2013\u2014]\s*", "", line).rstrip() for line in lines).strip()


def normalize_labeling_inputs(questions: list[str], cevap: str) -> tuple[list[str], str]:
    return [clean_labeling_field_text(q) for q in questions], clean_labeling_field_text(cevap)


def validate_labeling_submission(questions: list[str], cevap: str) -> None:
    if not questions or not [q for q in questions if q and q.strip()]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="En az bir soru girmelisiniz.")
    if not cevap or not cevap.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cevap alanı zorunludur.")


def validate_labeling_quality(document_text: str, questions: list[str], cevap: str) -> None:
    document_tokens = set(_quality_tokens(document_text))
    blockers: list[str] = []

    source_tokens = _quality_tokens(document_text)
    for index, question in enumerate([q for q in questions if q and q.strip()], start=1):
        blockers.extend(
            _quality_blockers_for_text(
                label=f"Soru {index}",
                value=question,
                document_tokens=document_tokens,
                source_tokens=source_tokens,
                min_tokens=MIN_QUESTION_QUALITY_TOKENS,
                min_document_overlap=MIN_QUESTION_DOCUMENT_OVERLAP,
            )
        )

    blockers.extend(
        _quality_blockers_for_text(
            label="Cevap",
            value=cevap,
            document_tokens=document_tokens,
            source_tokens=source_tokens,
            min_tokens=MIN_ANSWER_QUALITY_TOKENS,
            min_document_overlap=MIN_ANSWER_DOCUMENT_OVERLAP,
        )
    )
    if _has_incomplete_sentence_end(cevap):
        blockers.append(
            "Cevap cümlesi tamamlanmamış gibi görünüyor. Metin nokta ile bitmiyor; "
            "lütfen cevabı doğru şekilde tamamlayıp tam bir cümle olduğundan emin olup tekrar kaydedin."
        )

    if blockers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": blockers})


def generate_quality_warnings(
    document_text: str,
    questions: list[str],
    cevap: str,
    duration_seconds: int | None,
    raw_questions: list[str] | None = None,
    raw_cevap: str | None = None,
) -> list[str]:
    warnings: list[str] = []
    raw_questions = raw_questions or questions
    raw_cevap = cevap if raw_cevap is None else raw_cevap

    for i, q in enumerate(questions, start=1):
        if q and len(q.strip()) < 150:
            warnings.append(
                f"Soru {i} 150 karakterden kısa görünüyor. Sorunun bağlamını yeterince eklediğinizden emin misiniz?"
            )
        if _contains_any_marker(q, QUESTION_ENDING_MARKERS):
            warnings.append(
                f"Soru {i} içinde talep bitiş kalıbı görünüyor. `talep edildiği anlaşılmıştır`, `sorulmaktadır`, `talep edilmektedir`, `talep edildiği anlaşılmaktadır`, `görüşü istenilmektedir`, `talep ettiğiniz anlaşılmıştır`, `sorulduğu anlaşılmaktadır`, `talep ettiğiniz anlaşılmaktadır`, gibi kapanış ifadeleri soru alanına dahil edilmemelidir."
            )
        if _contains_any_marker(q, ANSWER_CLOSING_MARKERS):
            warnings.append(
                f"Soru {i} içinde `Bilgi edinilmesini rica ederim/arz ederim..`gibi kapanışı görünüyor. Bu kapanış soru alanına dahil edilmemelidir."
            )

    for i, raw_q in enumerate(raw_questions, start=1):
        if _has_leading_bullet(raw_q):
            warnings.append(
                f"Soru {i} satır başında `-` madde işareti içeriyor. Soru alanına kaydetmeden önce satır başındaki `-` işaretini silin."
            )

    if duration_seconds is not None and duration_seconds < 120:
        warnings.append(
            "Bu belgeyi çok kısa sürede tamamladınız. Soruların bağlamını yeterince incelediğinizden emin misiniz?"
        )

    if _has_leading_bullet(raw_cevap):
        warnings.append(
            "Cevap alanında satır başında `-` madde işareti görünüyor. Cevap alanına kaydetmeden önce satır başındaki `-` işaretini silin."
        )
    if _contains_any_marker(cevap[:400], QUESTION_ENDING_MARKERS):
        warnings.append(
            "Cevap alanı talep bitiş ifadesini içeriyor gibi görünüyor. Cevap genellikle `talep edildiği anlaşılmıştır`, `sorulmaktadır`, `talep edilmektedir`, `talep edildiği anlaşılmaktadır`, `görüşü istenilmektedir`, `talep ettiğiniz anlaşılmıştır`, `talep ettiğiniz anlaşılmaktadır`, gibi ifadelerden sonra başlamalıdır; bu ifadeler cevaba dahil edilmemelidir."
        )
    if _contains_any_marker(cevap, ANSWER_CLOSING_MARKERS):
        warnings.append(
            "Cevap alanında `Bilgi edinilmesini rica/arz ederim` kapanışı görünüyor. Mevcut kılavuza göre cevap kısmını bu kapanış cümlesi dahil olmayacak şekilde alın."
        )

    if len(_quality_tokens(cevap)) >= MIN_ANSWER_QUALITY_TOKENS and not _has_answer_conclusion_marker(cevap):
        warnings.append(
            "Cevap yalnızca mevzuat aktarımı gibi görünüyor; sonuç/uygulama kısmı eksik olabilir. "
            "Lütfen `Buna göre`, `Yukarıdaki hüküm ve açıklamalara göre`, `gerekmektedir` veya "
            "`mümkün bulunmamaktadır` gibi sonuç cümlelerini de aldığınızdan emin olun."
        )

    warnings.extend(_source_boundary_warnings(document_text, questions, cevap))

    return warnings


def _has_leading_bullet(value: str | None) -> bool:
    return bool(re.search(r"(?m)^\s*[-\u2013\u2014]\s*", value or ""))


def _contains_any_marker(value: str | None, markers: list[str]) -> bool:
    normalized = _normalize_for_marker_search(value)
    return any(_normalize_for_marker_search(marker) in normalized for marker in markers)


def _normalize_for_marker_search(value: str | None) -> str:
    text = str(value or "").replace("\u00a0", " ").casefold()
    return re.sub(r"\s+", " ", text).strip()


def _normalize_for_quality_phrase_search(value: str | None) -> str:
    text = str(value or "").replace("\u00a0", " ").casefold().replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip()


def _has_incomplete_sentence_end(value: str | None) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    return text[-1] not in ".!?"


def _source_boundary_warnings(document_text: str, questions: list[str], cevap: str) -> list[str]:
    zones = _extract_source_zones(document_text)
    if not zones:
        return []

    warnings: list[str] = []
    question_zone_tokens = set(_quality_tokens(zones["question_zone"]))
    answer_zone_tokens = _quality_tokens(zones["answer_zone"])
    answer_zone_token_set = set(answer_zone_tokens)

    for i, question in enumerate([q for q in questions if q and q.strip()], start=1):
        question_tokens = _quality_tokens(question)
        if len(question_tokens) < MIN_QUESTION_QUALITY_TOKENS:
            continue
        question_zone_overlap = _document_overlap_ratio(question_tokens, question_zone_tokens)
        answer_zone_overlap = _document_overlap_ratio(question_tokens, answer_zone_token_set)
        if (
            question_zone_overlap < MIN_SOURCE_ZONE_OVERLAP
            and answer_zone_overlap > question_zone_overlap
        ) or (
            answer_zone_overlap >= MIN_WRONG_ZONE_OVERLAP
            and answer_zone_overlap - question_zone_overlap >= MIN_ZONE_OVERLAP_GAP
        ):
            warnings.append(
                f"Soru {i}, özelge metnindeki talep/soru bölümünden çok cevap bölümüne benziyor. "
                "Lütfen soru metnini talep bitiş ifadesinden önceki kısımdan aldığınızı kontrol edin."
            )

    answer_tokens = _quality_tokens(cevap)
    if len(answer_tokens) >= MIN_ANSWER_QUALITY_TOKENS and answer_zone_tokens:
        answer_overlap = _document_overlap_ratio(answer_tokens, answer_zone_token_set)
        question_overlap = _document_overlap_ratio(answer_tokens, question_zone_tokens)
        if (
            answer_overlap < MIN_ANSWER_DOCUMENT_OVERLAP
            and question_overlap > answer_overlap
        ) or (
            question_overlap >= MIN_WRONG_ZONE_OVERLAP
            and question_overlap - answer_overlap >= MIN_ZONE_OVERLAP_GAP
        ):
            warnings.append(
                "Cevap alanı, özelge metnindeki cevap bölümünden çok talep/soru bölümüne benziyor. "
                "Lütfen cevabı talep bitiş ifadesinden sonraki kısımdan aldığınızı kontrol edin."
            )

        if zones["has_closing_marker"] and len(answer_zone_tokens) > ANSWER_EDGE_TOKEN_WINDOW:
            submitted_answer_tokens = set(answer_tokens)
            tail_tokens = answer_zone_tokens[-ANSWER_EDGE_TOKEN_WINDOW:]
            tail_overlap = _document_overlap_ratio(tail_tokens, submitted_answer_tokens)
            if tail_overlap < MIN_ANSWER_TAIL_OVERLAP:
                warnings.append(
                    "Cevap, kapanış cümlesinden önceki son sonuç paragraflarına kadar alınmamış olabilir. "
                    "`Bilgi edinilmesini rica/arz ederim` kapanışından hemen önceki bölümü de kontrol edin."
                )

    return warnings


def _extract_source_zones(document_text: str) -> dict[str, str | bool] | None:
    normalized = _normalize_for_quality_phrase_search(document_text)
    boundary = _find_first_marker(normalized, SOURCE_QUESTION_ANSWER_BOUNDARY_MARKERS)
    if not boundary:
        return None

    boundary_index, marker = boundary
    answer_start = boundary_index + len(marker)
    answer_zone = normalized[answer_start:].strip(" .:-;\n\t")
    closing = _find_last_marker(answer_zone, SOURCE_ANSWER_CLOSING_MARKERS)
    has_closing_marker = closing is not None
    if closing:
        answer_zone = answer_zone[: closing[0]].strip(" .:-;\n\t")

    return {
        "question_zone": normalized[:boundary_index].strip(),
        "answer_zone": answer_zone,
        "has_closing_marker": has_closing_marker,
    }


def _find_first_marker(value: str, markers: list[str]) -> tuple[int, str] | None:
    found: list[tuple[int, str]] = []
    for marker in markers:
        index = value.find(marker)
        if index >= 0:
            found.append((index, marker))
    return min(found, key=lambda item: item[0]) if found else None


def _find_last_marker(value: str, markers: list[str]) -> tuple[int, str] | None:
    found: list[tuple[int, str]] = []
    for marker in markers:
        index = value.rfind(marker)
        if index >= 0:
            found.append((index, marker))
    return max(found, key=lambda item: item[0]) if found else None


def _quality_tokens(value: str | None) -> list[str]:
    tokens = re.findall(r"[0-9A-Za-zÇĞİÖŞÜçğıöşü]{2,}", str(value or "").casefold())
    return [token for token in tokens if len(token) >= 3 and token not in TURKISH_STOPWORDS]


def _quality_blockers_for_text(
    label: str,
    value: str,
    document_tokens: set[str],
    min_tokens: int,
    min_document_overlap: float,
    require_conclusion_marker: bool = False,
    source_tokens: list[str] | None = None,
) -> list[str]:
    blockers: list[str] = []
    tokens = _quality_tokens(value)

    if (
        _has_repeated_letter_run(value)
        or _has_repeated_digit_run(value)
        or _has_keyboard_junk(value)
        or _has_low_vowel_ratio(value)
    ):
        blockers.append(
            f"{label} rastgele veya aynı karakterlerin tekrarından oluşan metin gibi görünüyor. "
            "Lütfen özelge metnindeki gerçek içeriği girin."
        )

    if _has_suspicious_repetition(tokens, source_tokens):
        blockers.append(f"{label} aynı kelimelerin aşırı tekrarından oluşuyor. Lütfen gerçek soru/cevap metnini girin.")

    if _has_suspicious_phrase_repetition(tokens, source_tokens):
        blockers.append(
            f"{label} aynı ifade veya cümle parçalarının tekrar eden kopyası gibi görünüyor. "
            "Lütfen özelge metnindeki gerçek cevap bölümünü bir kez, olduğu gibi girin."
        )

    if len(tokens) < min_tokens:
        blockers.append(f"{label} anlamlı içerik bakımından çok kısa görünüyor. Lütfen özelge metninden ilgili bölümü yazın.")
        return blockers

    if require_conclusion_marker and not _has_answer_conclusion_marker(value):
        blockers.append(
            f"{label} yalnızca mevzuat aktarımı gibi görünüyor; sonuç/uygulama kısmı eksik olabilir. "
            "Lütfen `Buna göre`, `Yukarıda yer alan hüküm ve açıklamalar çerçevesinde`, "
            "`gerekmektedir` veya `mümkün bulunmamaktadır` gibi sonuç cümlelerini de içeren cevap bölümünü yazın."
        )

    overlap = _document_overlap_ratio(tokens, document_tokens)
    if overlap < min_document_overlap:
        blockers.append(
            f"{label} özelge metniyle yeterince örtüşmüyor. Lütfen belge içindeki ilgili talep veya cevap bölümünü kullanın."
        )

    return blockers


def _has_repeated_character_run(value: str | None) -> bool:
    return _has_repeated_letter_run(value) or _has_repeated_digit_run(value)


def _has_repeated_letter_run(value: str | None) -> bool:
    text = str(value or "").casefold()
    # Form sablonlarindaki "......" yer tutucularini elemek icin yalnizca harf tekrarina bak.
    pattern = rf"([a-zçğıöşü])\1{{{MIN_REPEATED_LETTER_RUN - 1},}}"
    return bool(re.search(pattern, text, flags=re.UNICODE))


def _has_repeated_digit_run(value: str | None) -> bool:
    text = str(value or "").casefold()
    # Fatura/seri numaralarindaki sifir dolgularini elemek icin yalnizca bagimsiz rakam tekrarina bak.
    alnum = "0-9a-zçğıöşü"
    pattern = rf"(?<![{alnum}])(\d)\1{{{MIN_REPEATED_DIGIT_RUN - 1},}}(?![{alnum}])"
    return bool(re.search(pattern, text, flags=re.UNICODE))


def _has_keyboard_junk(value: str | None) -> bool:
    normalized = re.sub(r"\s+", "", str(value or "").casefold())
    junk_patterns = [
        "asdf",
        "qwer",
        "zxcv",
        "sdfg",
        "dfgh",
        "hjkl",
        "123123",
        "123456",
        "abcdef",
        "qazwsx",
    ]
    return any(pattern in normalized for pattern in junk_patterns)


def _has_low_vowel_ratio(value: str | None) -> bool:
    letters = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", str(value or "").casefold())
    if len(letters) < 30:
        return False
    vowels = sum(1 for letter in letters if letter in "aeıioöuü")
    return vowels / len(letters) < MIN_VOWEL_RATIO


def _has_consecutive_token_run(tokens: list[str], token: str, run_length: int) -> bool:
    if run_length < MIN_CONSECUTIVE_REPEATED_TOKENS or len(tokens) < run_length:
        return False

    for index in range(len(tokens) - run_length + 1):
        if all(tokens[index + offset] == token for offset in range(run_length)):
            return True
    return False


def _find_repeated_runs(tokens: list[str], min_run: int = MIN_CONSECUTIVE_REPEATED_TOKENS) -> list[tuple[str, int]]:
    if len(tokens) < min_run:
        return []

    runs: list[tuple[str, int]] = []
    current_token = tokens[0]
    current_run = 1
    for token in tokens[1:]:
        if token == current_token:
            current_run += 1
            if current_run >= min_run:
                runs.append((current_token, current_run))
        else:
            current_token = token
            current_run = 1
    return runs


def _has_repetition_pattern(tokens: list[str]) -> bool:
    return bool(_find_repeated_runs(tokens))


def _has_suspicious_repetition(tokens: list[str], source_tokens: list[str] | None) -> bool:
    repeated_runs = _find_repeated_runs(tokens)
    if not repeated_runs:
        return False
    if not source_tokens:
        return True

    for token, run_length in repeated_runs:
        if not _has_consecutive_token_run(source_tokens, token, run_length):
            return True
    return False


def _count_token_ngrams(tokens: list[str], n: int) -> dict[tuple[str, ...], int]:
    counts: dict[tuple[str, ...], int] = {}
    if len(tokens) < n:
        return counts
    for index in range(len(tokens) - n + 1):
        gram = tuple(tokens[index : index + n])
        counts[gram] = counts.get(gram, 0) + 1
    return counts


def _has_suspicious_phrase_repetition(
    tokens: list[str],
    source_tokens: list[str] | None,
    *,
    n: int = MIN_PHRASE_REPETITION_NGRAM,
    min_count: int = MIN_PHRASE_REPETITION_COUNT,
) -> bool:
    if len(tokens) < n * min_count:
        return False

    submitted_counts = _count_token_ngrams(tokens, n)
    source_counts = _count_token_ngrams(source_tokens or [], n)
    for gram, count in submitted_counts.items():
        if count >= min_count and source_counts.get(gram, 0) < min_count:
            return True
    return False


def _has_answer_conclusion_marker(value: str | None) -> bool:
    normalized = _normalize_for_quality_phrase_search(value)
    return any(marker in normalized for marker in ANSWER_CONCLUSION_MARKERS)


def _document_overlap_ratio(tokens: list[str], document_tokens: set[str]) -> float:
    if not tokens or not document_tokens:
        return 0.0
    matched = sum(1 for token in tokens if token in document_tokens)
    return matched / len(tokens)


def create_labeling_record(
    db: Session,
    user_id: int,
    document_id: int,
    questions: list[str],
    cevap: str,
    duration_seconds: int | None,
) -> LabelingRecord:
    # Belge başına en fazla bir etiketleme: belge için HERHANGİ bir kullanıcının
    # kaydı varsa yeni kayıt açılamaz (lease boşluğunda mükerrer etiketlemeyi keser).
    existing = db.execute(
        select(LabelingRecord.user_id).where(LabelingRecord.document_id == document_id)
    ).first()
    if existing:
        if existing.user_id == user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu belgeyi zaten siz etiketlemişsiniz.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu belge başka bir kullanıcı tarafından etiketlendi; lütfen yeni belgeye geçin.",
        )

    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Belge bulunamadı.")
    if doc.split not in (DocumentSplit.annotation, DocumentSplit.training):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu belge etiketleme için uygun değil.")

    # Belge etiketlendi: kuyruk rezervasyonunu temizle (tabloyu temiz tut).
    doc.reserved_by_user_id = None
    doc.reserved_at = None

    rec = LabelingRecord(
        user_id=user_id,
        document_id=document_id,
        cevap=cevap.strip(),
        doldurulan_soru_kutucugu_sayisi=len([q for q in questions if q and q.strip()]),
        belgeyi_tamamlama_suresi=timedelta(seconds=duration_seconds) if duration_seconds is not None else None,
        belge_tamamlama_tarihi=datetime.now(timezone.utc),
    )
    db.add(rec)
    db.flush()

    order = 1
    for q in questions:
        qt = (q or "").strip()
        if not qt:
            continue
        db.add(LabelingQuestion(labeling_record_id=rec.id, question_order=order, question_text=qt))
        order += 1

    try:
        db.commit()
    except IntegrityError:
        # Aynı belgeyi iki kullanıcının tam eşzamanlı kaydetmesi (check-then-insert
        # yarışı): DB'deki belge-başına-tek-kayıt unique index'i ikinciyi reddeder.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu belge başka bir kullanıcı tarafından etiketlendi; lütfen yeni belgeye geçin.",
        )
    db.refresh(rec)
    return rec


def labeling_record_to_out(r: LabelingRecord) -> LabelingRecordOut:
    seconds: int | None = None
    if r.belgeyi_tamamlama_suresi is not None:
        try:
            seconds = int(r.belgeyi_tamamlama_suresi.total_seconds())
        except Exception:
            seconds = None
    qs = sorted(r.questions, key=lambda q: q.question_order)
    return LabelingRecordOut(
        id=r.id,
        document_id=r.document_id,
        evrak_id=r.document.evrak_id if r.document else "",
        soru_sayisi=r.doldurulan_soru_kutucugu_sayisi,
        cevap=r.cevap,
        belgeyi_tamamlama_suresi_seconds=seconds,
        belge_tamamlama_tarihi=r.belge_tamamlama_tarihi,
        created_at=r.created_at,
        questions=[
            LabelingQuestionOut(question_order=q.question_order, question_text=q.question_text, character_count=q.character_count)
            for q in qs
        ],
    )


def labeling_record_summary_to_out(r: LabelingRecord) -> LabelingRecordSummaryOut:
    seconds: int | None = None
    if r.belgeyi_tamamlama_suresi is not None:
        try:
            seconds = int(r.belgeyi_tamamlama_suresi.total_seconds())
        except Exception:
            seconds = None
    return LabelingRecordSummaryOut(
        id=r.id,
        document_id=r.document_id,
        evrak_id=r.document.evrak_id if r.document else "",
        soru_sayisi=r.doldurulan_soru_kutucugu_sayisi,
        belgeyi_tamamlama_suresi_seconds=seconds,
        belge_tamamlama_tarihi=r.belge_tamamlama_tarihi,
        created_at=r.created_at,
    )


def fetch_labeling_record_by_id(db: Session, record_id: int) -> LabelingRecord | None:
    stmt = (
        select(LabelingRecord)
        .where(LabelingRecord.id == record_id)
        .options(selectinload(LabelingRecord.questions), selectinload(LabelingRecord.document))
    )
    return db.execute(stmt).scalar_one_or_none()


def ensure_can_modify_labeling_record(current_user: User, rec: LabelingRecord) -> None:
    if current_user.role == UserRole.admin:
        return
    if rec.user_id == current_user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu kaydı düzenleme yetkiniz yok.")


def update_labeling_record(
    db: Session,
    record: LabelingRecord,
    questions: list[str],
    cevap: str,
    duration_seconds: int | None,
) -> LabelingRecord:
    doc = db.get(Document, record.document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Belge bulunamadı.")
    if doc.split not in (DocumentSplit.annotation, DocumentSplit.training):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu belge etiketleme için uygun değil.")

    record.cevap = cevap.strip()
    record.doldurulan_soru_kutucugu_sayisi = len([q for q in questions if q and q.strip()])
    record.belgeyi_tamamlama_suresi = timedelta(seconds=duration_seconds) if duration_seconds is not None else None
    record.belge_tamamlama_tarihi = datetime.now(timezone.utc)

    db.execute(delete(LabelingQuestion).where(LabelingQuestion.labeling_record_id == record.id))
    db.flush()

    order = 1
    for q in questions:
        qt = (q or "").strip()
        if not qt:
            continue
        db.add(LabelingQuestion(labeling_record_id=record.id, question_order=order, question_text=qt))
        order += 1

    db.commit()
    refreshed = fetch_labeling_record_by_id(db, record.id)
    if not refreshed:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Kayıt yenilenemedi.")
    return refreshed


def _count_records_on_day(db: Session, user_id: int, day: date) -> int:
    return int(
        db.execute(
            select(func.count(LabelingRecord.id)).where(
                LabelingRecord.user_id == user_id,
                func.date(LabelingRecord.created_at) == day,
            )
        ).scalar_one()
    )


def _get_daily_counts(db: Session, user_id: int, days: int = 7) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    rows = db.execute(
        select(func.date(LabelingRecord.created_at).label("day"), func.count(LabelingRecord.id).label("count"))
        .where(LabelingRecord.user_id == user_id, func.date(LabelingRecord.created_at) >= start)
        .group_by(func.date(LabelingRecord.created_at))
        .order_by(func.date(LabelingRecord.created_at))
    ).all()
    counts_by_day = {str(row.day): int(row.count or 0) for row in rows}
    return [
        {"date": str(start + timedelta(days=offset)), "count": counts_by_day.get(str(start + timedelta(days=offset)), 0)}
        for offset in range(days)
    ]


def _calculate_leaderboard_score(completed_count: int, today_completed_count: int, dragon_count: int) -> int:
    return (
        completed_count * LEADERBOARD_COMPLETED_POINTS
        + today_completed_count * LEADERBOARD_TODAY_BONUS_POINTS
        + dragon_count * LEADERBOARD_DRAGON_POINTS
    )


def _ensure_dragon_reward_for_day(
    db: Session,
    user_id: int,
    day: date,
    milestone: int = 0,
) -> DragonReward:
    existing = db.execute(
        select(DragonReward).where(
            DragonReward.user_id == user_id,
            DragonReward.reward_date == day,
            DragonReward.milestone == milestone,
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    seed = user_id * 31 + day.toordinal() + milestone * 997
    color = DRAGON_COLORS[seed % len(DRAGON_COLORS)]
    name = DRAGON_NAMES[(seed // len(DRAGON_COLORS)) % len(DRAGON_NAMES)]
    reward = DragonReward(
        user_id=user_id,
        reward_date=day,
        milestone=milestone,
        color=color,
        name=name,
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


def ensure_first_dragon_reward(db: Session, user_id: int, day: date | None = None) -> DragonReward:
    existing = db.execute(
        select(DragonReward)
        .where(DragonReward.user_id == user_id)
        .order_by(DragonReward.reward_date.asc(), DragonReward.id.asc())
    ).scalars().first()
    if existing:
        return existing
    return _ensure_dragon_reward_for_day(db, user_id, day or datetime.now(timezone.utc).date(), milestone=0)


def _list_dragon_rewards(db: Session, user_id: int) -> list[DragonReward]:
    return db.execute(
        select(DragonReward)
        .where(DragonReward.user_id == user_id)
        .order_by(DragonReward.reward_date.desc(), DragonReward.id.desc())
    ).scalars().all()


def _build_motivation_messages(
    today_completed: int,
    yesterday_completed: int,
    previous_best: int,
    dragon_awarded_today: bool,
    dragon_award_reason: str = "threshold",
) -> list[dict]:
    messages: list[dict] = []
    delta = today_completed - yesterday_completed

    if delta > 0 and yesterday_completed > 0:
        messages.append(
            {
                "kind": "improved",
                "title": "Dünkü ritmi geçtiniz",
                "message": f"Bugün dünden {delta} belge daha fazla etiketlediniz. Bu net bir yükseliş.",
            }
        )
    elif today_completed > 0 and yesterday_completed == 0:
        messages.append(
            {
                "kind": "started",
                "title": "Bugünün serisi başladı",
                "message": f"Bugün {today_completed} belge tamamladınız. Seriyi buradan büyütebilirsiniz.",
            }
        )

    if today_completed > previous_best and today_completed > 0:
        messages.append(
            {
                "kind": "best",
                "title": "Yeni günlük zirve",
                "message": f"Bugünkü {today_completed} belge, önceki en iyi günlük skorunuzu geçti.",
            }
        )

    if dragon_awarded_today and dragon_award_reason == "first":
        messages.append(
            {
                "kind": "dragon",
                "title": "İlk yumurta çatladı",
                "message": "Mini sınavı geçtiniz. İlk ejderhanız koleksiyonunuzda sizi bekliyor.",
            }
        )
    elif dragon_awarded_today:
        messages.append(
            {
                "kind": "dragon",
                "title": "Surpriz yumurta catladi",
                "message": "Yeni bir 25 belgelik eşiği geçtiniz. Ejderhanız koleksiyonunuza katıldı.",
            }
        )
    elif DRAGON_THRESHOLD - (today_completed % DRAGON_THRESHOLD) <= 5:
        remaining = DRAGON_THRESHOLD - (today_completed % DRAGON_THRESHOLD)
        messages.append(
            {
                "kind": "near-dragon",
                "title": "Ejderha yumurtası ısınıyor",
                "message": f"{remaining} belge sonra sıradaki sürpriz yumurta çatlayacak.",
            }
        )

    if not messages:
        messages.append(
            {
                "kind": "steady",
                "title": "Küçük adımlar da sayılır",
                "message": "Bugün bir belgeyle başlamak bile ritmi geri getirir.",
            }
        )

    return messages


def get_user_progress(db: Session, user_id: int) -> dict:
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    completed = db.execute(select(func.count(LabelingRecord.id)).where(LabelingRecord.user_id == user_id)).scalar_one()
    today_completed = _count_records_on_day(db, user_id, today)
    yesterday_completed = _count_records_on_day(db, user_id, yesterday)
    daily_counts = _get_daily_counts(db, user_id)
    previous_best = max((row["count"] for row in daily_counts[:-1]), default=0)
    best_daily = max((row["count"] for row in daily_counts), default=0)
    dragon_awarded_today = False
    dragon_award_reason = "threshold"

    earned_daily_dragons = _earned_daily_dragon_count(today_completed)
    existing_milestones = set(
        db.execute(
            select(DragonReward.milestone).where(
                DragonReward.user_id == user_id,
                DragonReward.reward_date == today,
                DragonReward.milestone > 0,
            )
        ).scalars()
    )
    for milestone in range(1, earned_daily_dragons + 1):
        if milestone not in existing_milestones:
            _ensure_dragon_reward_for_day(db, user_id, today, milestone=milestone)
            dragon_awarded_today = True

    dragon_rewards = _list_dragon_rewards(db, user_id)
    if not dragon_awarded_today and today_completed < DRAGON_THRESHOLD:
        today_first_dragon = (
            len(dragon_rewards) == 1
            and dragon_rewards[0].reward_date == today
            and dragon_rewards[0].created_at.date() == today
        )
        if today_first_dragon:
            dragon_awarded_today = True
            dragon_award_reason = "first"
    avg_seconds = db.execute(
        select(func.avg(func.extract("epoch", LabelingRecord.belgeyi_tamamlama_suresi))).where(
            LabelingRecord.user_id == user_id, LabelingRecord.belgeyi_tamamlama_suresi.is_not(None)
        )
    ).scalar_one()
    return {
        "completed_count": int(completed),
        "today_completed_count": today_completed,
        "yesterday_completed_count": yesterday_completed,
        "improvement_delta": today_completed - yesterday_completed,
        "best_daily_count": best_daily,
        "previous_best_daily_count": previous_best,
        "daily_counts": daily_counts,
        "motivation_messages": _build_motivation_messages(
            today_completed=today_completed,
            yesterday_completed=yesterday_completed,
            previous_best=previous_best,
            dragon_awarded_today=dragon_awarded_today,
            dragon_award_reason=dragon_award_reason,
        ),
        "dragon_rewards": [
            {
                "id": reward.id,
                "reward_date": str(reward.reward_date),
                "milestone": reward.milestone,
                "color": reward.color,
                "name": reward.name,
                "created_at": reward.created_at,
            }
            for reward in dragon_rewards
        ],
        "dragon_awarded_today": dragon_awarded_today,
        "avg_duration_seconds": float(avg_seconds) if avg_seconds is not None else None,
        "total_score": _calculate_leaderboard_score(int(completed), today_completed, len(dragon_rewards)),
    }


def get_leaderboard(db: Session, current_user_id: int, limit: int = 10) -> dict:
    today = datetime.now(timezone.utc).date()
    completed_subq = (
        select(
            LabelingRecord.user_id.label("user_id"),
            func.count(LabelingRecord.id).label("completed_count"),
            func.avg(func.extract("epoch", LabelingRecord.belgeyi_tamamlama_suresi)).label("avg_duration_seconds"),
        )
        .group_by(LabelingRecord.user_id)
        .subquery()
    )
    today_subq = (
        select(LabelingRecord.user_id.label("user_id"), func.count(LabelingRecord.id).label("today_completed_count"))
        .where(func.date(LabelingRecord.created_at) == today)
        .group_by(LabelingRecord.user_id)
        .subquery()
    )
    dragon_subq = (
        select(DragonReward.user_id.label("user_id"), func.count(DragonReward.id).label("dragon_count"))
        .group_by(DragonReward.user_id)
        .subquery()
    )

    completed_count_expr = func.coalesce(completed_subq.c.completed_count, 0)
    today_completed_count_expr = func.coalesce(today_subq.c.today_completed_count, 0)
    dragon_count_expr = func.coalesce(dragon_subq.c.dragon_count, 0)
    total_score_expr = (
        completed_count_expr * LEADERBOARD_COMPLETED_POINTS
        + today_completed_count_expr * LEADERBOARD_TODAY_BONUS_POINTS
        + dragon_count_expr * LEADERBOARD_DRAGON_POINTS
    )

    rows = db.execute(
        select(
            User.id,
            User.kullanici_adi,
            completed_count_expr.label("completed_count"),
            today_completed_count_expr.label("today_completed_count"),
            completed_subq.c.avg_duration_seconds,
            dragon_count_expr.label("dragon_count"),
            total_score_expr.label("total_score"),
        )
        .where(User.role.in_([UserRole.labeler, UserRole.admin]), User.exam_passed.is_(True))
        .outerjoin(completed_subq, completed_subq.c.user_id == User.id)
        .outerjoin(today_subq, today_subq.c.user_id == User.id)
        .outerjoin(dragon_subq, dragon_subq.c.user_id == User.id)
        .order_by(
            total_score_expr.desc(),
            completed_count_expr.desc(),
            today_completed_count_expr.desc(),
            dragon_count_expr.desc(),
            User.kullanici_adi.asc(),
        )
    ).all()

    ranked: list[dict] = []
    current_entry: dict | None = None
    for index, row in enumerate(rows, start=1):
        entry = {
            "rank": index,
            "user_id": row.id,
            "kullanici_adi": row.kullanici_adi,
            "completed_count": int(row.completed_count or 0),
            "today_completed_count": int(row.today_completed_count or 0),
            "avg_duration_seconds": float(row.avg_duration_seconds) if row.avg_duration_seconds is not None else None,
            "dragon_count": int(row.dragon_count or 0),
            "total_score": int(row.total_score or 0),
            "is_current_user": row.id == current_user_id,
        }
        if row.id == current_user_id:
            current_entry = entry
        if len(ranked) < limit:
            ranked.append(entry)

    return {"entries": ranked, "current_user": current_entry}


def get_user_records(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 25,
    evrak_id: str | None = None,
    sort: str = "newest",
) -> tuple[list[LabelingRecord], int]:
    filters = [LabelingRecord.user_id == user_id]
    normalized_evrak_id = evrak_id.strip() if evrak_id else ""
    if normalized_evrak_id:
        filters.append(Document.evrak_id.ilike(f"%{normalized_evrak_id}%"))

    total_stmt = select(func.count(LabelingRecord.id)).join(Document, Document.id == LabelingRecord.document_id).where(*filters)
    total = int(db.execute(total_stmt).scalar_one())
    offset = (page - 1) * page_size
    order_by = [LabelingRecord.created_at.desc()]
    if sort == "question_count_asc":
        order_by = [
            LabelingRecord.doldurulan_soru_kutucugu_sayisi.asc(),
            LabelingRecord.created_at.desc(),
        ]
    stmt = (
        select(LabelingRecord)
        .join(Document, Document.id == LabelingRecord.document_id)
        .where(*filters)
        .options(
            joinedload(LabelingRecord.document).load_only(Document.id, Document.evrak_id),
        )
        .order_by(*order_by)
        .offset(offset)
        .limit(page_size)
    )
    return db.execute(stmt).scalars().all(), total
