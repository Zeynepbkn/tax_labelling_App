from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.db.models.document import Document, DocumentSplit
from app.db.models.dragon_reward import DragonReward
from app.db.models.quiz import QuizOption, QuizQuestion
from app.db.models.user import User, UserRole
from app.services.document_service import import_training_documents
from app.services.labeling_service import ensure_first_dragon_reward


logger = logging.getLogger("taxlabeltr.bootstrap")

DEFAULT_QUIZ_QUESTIONS = [
    {
        "question_text": "Özelge etiketlemede temel görev nedir?",
        "option_a": "Belgenin tamamını kısaltmadan cevap alanına kopyalamak",
        "option_b": "Sadece vergi türünü seçmek",
        "option_c": "Mükellefin talep veya sorularını bağlamıyla çıkarmak ve idarenin cevabını ayırmak",
        "option_d": "Her belge için tek kelimelik soru yazmak",
        "correct_option": QuizOption.c,
        "explanation": "Etiketleyici, mükellefin sorusunu ve idarenin değerlendirme/cevap kısmını ayrı alanlarda yakalar.",
        "active": True,
    },
    {
        "question_text": "Soru kutusuna nasıl bir ifade yazılmalıdır?",
        "option_a": "Metinden bağımsız, genel bir başlık",
        "option_b": "Mükellefin talebini anlatan, yeterli bağlam içeren açık bir soru",
        "option_c": "Yalnızca kanun numarası",
        "option_d": "Boş bırakılabilir",
        "correct_option": QuizOption.b,
        "explanation": "Soru, metindeki talebi başka bir okuyucunun anlayabileceği kadar bağlamlı olmalıdır.",
        "active": True,
    },
    {
        "question_text": "Cevap alanı genellikle hangi kısımdan başlar?",
        "option_a": "Belgenin evrak numarasından",
        "option_b": "Mükellefin ilk cümlesinden",
        "option_c": "Talep anlatımı bittikten sonra idarenin hukuki değerlendirme ve sonuç kısmından",
        "option_d": "Sadece imza bölümünden",
        "correct_option": QuizOption.c,
        "explanation": "Cevap alanı, talep özetinden sonra gelen idare görüşü ve değerlendirme bölümüdür.",
        "active": True,
    },
    {
        "question_text": "Bir özelgede birden fazla ayrı talep varsa ne yapılmalıdır?",
        "option_a": "Sadece ilk talep yazılmalıdır",
        "option_b": "Her anlamlı talep için ayrı soru kutusu doldurulmalı ve ortak bağlam her soruda korunmalıdır",
        "option_c": "Tüm talepler silinmelidir",
        "option_d": "Belge atlanmalıdır",
        "correct_option": QuizOption.b,
        "explanation": "Ayrı talepler ayrı soru kutularına yazılır; ortak olay ve bağlam sadece ilk soruda bırakılmaz, her soru için tekrar eklenir.",
        "active": True,
    },
    {
        "question_text": "Talep anlatımını soru alanına aktarırken talep bitiş kalıpları nasıl ele alınmalıdır?",
        "option_a": "'Talep edilmektedir' gibi bitiş kalıpları soru metnine aynen eklenmelidir",
        "option_b": "Bu kalıplar çıkarılmalı; talep, bağlamıyla birlikte soru haline getirilmelidir",
        "option_c": "Yalnızca bitiş kalıbı yazılmalıdır",
        "option_d": "Cevap alanı boş bırakılmalıdır",
        "correct_option": QuizOption.b,
        "explanation": "'Talep edilmektedir' veya 'görüş talep edilmektedir' gibi kapanış kalıpları soru metnine eklenmez; talep anlamlı bir soru olarak tamamlanır.",
        "active": True,
    },
    {
        "question_text": "Özelge metninde talep ifadesi soru köküyle bitmiyorsa ne yapılmalıdır?",
        "option_a": "Talep olduğu gibi eksik bir ifadeyle bırakılmalıdır",
        "option_b": "Bağlam korunarak soru haline getirilmeli; bu tür kalıplar genellikle 'nedir?' sorusuyla tamamlanmalıdır",
        "option_c": "Belgenin tamamı soru alanına kopyalanmalıdır",
        "option_d": "Bu belge mutlaka atlanmalıdır",
        "correct_option": QuizOption.b,
        "explanation": "Örneğin 'uygulanacak KDV oranı', 'vergilendirilmesi' veya 'Kanunları karşısındaki durumu' gibi kalıplar 'nedir?' sorusuyla tamamlanır.",
        "active": True,
    },
    {
        "question_text": "'Kanunları karşısındaki durumu hususunda görüş talep edilmektedir' kalıbı soru olarak nasıl yazılmalıdır?",
        "option_a": "'Kanunları karşısındaki durumu hususunda görüş talep edilmektedir' aynen yazılmalıdır",
        "option_b": "'Kanunları karşısındaki durumu nedir?' şeklinde tamamlanmalıdır",
        "option_c": "Bu kısım cevap alanına alınmalıdır",
        "option_d": "Sadece 'görüş talep edilmektedir' yazılmalıdır",
        "correct_option": QuizOption.b,
        "explanation": "Soru kipi olmayan bu kalıpta 'hususunda görüş talep edilmektedir' bölümü çıkarılır ve anlam 'nedir?' sorusuyla tamamlanır.",
        "active": True,
    },
    {
        "question_text": "Gerçek etiketleme havuzuna geçmek için ne gereklidir?",
        "option_a": "Sadece kayıt olmak yeterlidir",
        "option_b": "Admin rolüne geçmek gerekir",
        "option_c": "Eğitim sayfasını hiç açmamak gerekir",
        "option_d": "Mini sınavdan geçme puanını almak gerekir",
        "correct_option": QuizOption.d,
        "explanation": "Etiketleyici kullanıcılar, gerçek etiketlemeye başlamadan önce mini sınavdan geçmelidir.",
        "active": True,
    },
]


REMOVED_QUIZ_QUESTION_TEXTS = (
    "Soru kısmına kopyalanan metinde satır başında '-' madde işareti varsa ne yapılmalıdır?",
    "Soru kismina kopyalanan metinde satir basinda '-' madde isareti varsa ne yapilmalidir?",
    "Soru veya cevap kısmına kopyalanan metinde satır başında '-' madde işareti varsa ne yapılmalıdır?",
    "Soru veya cevap kismina kopyalanan metinde satir basinda '-' madde isareti varsa ne yapilmalidir?",
    "'Kanunlari karsisindaki durumu hususunda gorus talep edilmektedir' kalibi soru olarak nasil yazilmalidir?",
    "'Kanunlari karsisindaki durumu hususunda gorus talep edilmektedir' kalibi soru olarak nasil yazilmalidir",
    "Kanunlari karsisindaki durumu hususunda gorus talep edilmektedir kalibi soru olarak nasil yazilmalidir?",
    "Kanunlari karsisindaki durumu hususunda gorus talep edilmektedir kalibi soru olarak nasil yazilmalidir",
)


OLD_QUIZ_QUESTION_TEXTS_BY_INDEX = {
    0: (
        "Ozelge " + "label" + "lamada temel gorev nedir?",
        "Ozelge etiketlemede temel gorev nedir?",
    ),
    1: ("Soru kutusuna nasil bir ifade yazilmalidir?",),
    2: ("Cevap alani genellikle hangi kisimdan baslar?",),
    3: ("Bir ozelgede birden fazla ayri talep varsa ne yapilmalidir?",),
    4: (
        "Ayni belgede uc farkli talep varsa ortak olay/baglam kismi nasil kullanilmalidir?",
        "Talep anlatimini soru alanina aktarirken talep bitis kaliplari nasil ele alinmalidir?",
    ),
    5: ("Ozelge metninde talep ifadesi soru kokuyle bitmiyorsa ne yapilmalidir?",),
    6: ("'Kanunlari karsisindaki durumu hususunda gorus talep edilmektedir' kalibi soru olarak nasil yazilmalidir?",),
    7: (
        "Gercek " + "label" + "lama havuzuna gecmek icin ne gereklidir?",
        "Gercek etiketleme havuzuna gecmek icin ne gereklidir?",
    ),
}


QUIZ_QUESTION_REPLACEMENTS = {
    old_text: DEFAULT_QUIZ_QUESTIONS[index]
    for index, old_texts in OLD_QUIZ_QUESTION_TEXTS_BY_INDEX.items()
    for old_text in old_texts
}


def _apply_quiz_question_payload(question: QuizQuestion, payload: dict) -> None:
    for key, value in payload.items():
        setattr(question, key, value)


def _quiz_question_key(text: str | None) -> str:
    return " ".join(str(text or "").casefold().split())


def deactivate_duplicate_active_quiz_questions(db: Session) -> int:
    active_questions = db.execute(
        select(QuizQuestion).where(QuizQuestion.active.is_(True)).order_by(QuizQuestion.id.asc())
    ).scalars().all()
    seen: set[str] = set()
    deactivated_count = 0
    for question in active_questions:
        key = _quiz_question_key(question.question_text)
        if key and key in seen:
            question.active = False
            db.add(question)
            deactivated_count += 1
            logger.info("deactivated duplicate active quiz question id=%s", question.id)
            continue
        seen.add(key)
    return deactivated_count


def deactivate_removed_quiz_questions(db: Session) -> int:
    removed_questions = db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.active.is_(True), QuizQuestion.question_text.in_(REMOVED_QUIZ_QUESTION_TEXTS))
        .order_by(QuizQuestion.id.asc())
    ).scalars().all()
    for question in removed_questions:
        question.active = False
        db.add(question)
        logger.info("deactivated removed quiz question id=%s", question.id)
    return len(removed_questions)


def ensure_default_quiz_questions(db: Session) -> None:
    removed_count = deactivate_removed_quiz_questions(db)
    updated_count = 0
    for old_text, new_payload in QUIZ_QUESTION_REPLACEMENTS.items():
        old_questions = db.execute(
            select(QuizQuestion).where(QuizQuestion.question_text == old_text).order_by(QuizQuestion.id.asc())
        ).scalars().all()
        for old_question in old_questions:
            existing_new = db.execute(
                select(QuizQuestion)
                .where(QuizQuestion.question_text == new_payload["question_text"], QuizQuestion.id != old_question.id)
                .order_by(QuizQuestion.id.asc())
            ).scalars().first()
            if existing_new:
                old_question.active = False
                db.add(old_question)
                logger.info("deactivated duplicate quiz question old_text=%s", old_text)
            else:
                _apply_quiz_question_payload(old_question, new_payload)
                db.add(old_question)
                logger.info("updated quiz question old_text=%s", old_text)
            updated_count += 1

    duplicate_count = deactivate_duplicate_active_quiz_questions(db)

    if removed_count or updated_count or duplicate_count:
        db.commit()

    existing_texts = set(db.execute(select(QuizQuestion.question_text)).scalars().all())
    missing_questions = [
        QuizQuestion(**payload) for payload in DEFAULT_QUIZ_QUESTIONS if payload["question_text"] not in existing_texts
    ]
    if not missing_questions:
        return

    db.add_all(missing_questions)
    db.commit()
    logger.info("seeded default quiz questions count=%s", len(missing_questions))


def ensure_training_examples(db: Session) -> None:
    existing_count = db.execute(
        select(func.count(Document.id)).where(Document.split == DocumentSplit.training)
    ).scalar_one()
    if existing_count:
        return

    data_path = Path(__file__).resolve().parents[3] / "labelled_questions.json"
    if not data_path.exists():
        logger.warning("training seed skipped; file not found path=%s", data_path)
        return

    with data_path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        logger.warning("training seed skipped; JSON root is not a list path=%s", data_path)
        return

    result = import_training_documents(db, data)
    logger.info(
        "seeded training examples added=%s skipped=%s duplicates=%s",
        result.get("added"),
        result.get("skipped"),
        result.get("duplicates"),
    )


def ensure_first_dragons_for_exam_passed_users(db: Session) -> None:
    rows = db.execute(
        select(User)
        .where(User.role.in_([UserRole.admin, UserRole.labeler]), User.exam_passed.is_(True))
        .where(~select(DragonReward.id).where(DragonReward.user_id == User.id).exists())
    ).scalars().all()
    for user in rows:
        ensure_first_dragon_reward(db, user.id)
    if rows:
        logger.info("seeded first dragon rewards for exam-passed users count=%s", len(rows))


def ensure_seed_data() -> None:
    with SessionLocal() as db:
        ensure_default_quiz_questions(db)
        ensure_training_examples(db)
        ensure_first_dragons_for_exam_passed_users(db)
