from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db.models.document import Document
from app.db.models.quiz import QuizAttempt, QuizQuestion
from app.db.models.training import TrainingLabel
from app.db.models.user import User
from app.services.labeling_service import ensure_first_dragon_reward
from app.services.text_normalization_service import normalize_document_whitespace


PRACTICAL_QUIZ_LABEL_IDS: list[int] = [410, 411, 414, 402, 387, 418, 419]

PRACTICAL_QUIZ_FOCUS: dict[int, str] = {
    419: "Soru kipi olmayan `uygulanacak KDV oranı` ifadelerini `nedir` ile tamamlayın.",
    387: "`vergilendirilmesi hususunda görüş talep edilmektedir` kalıbını soru haline getirin.",
    410: "Aynı belgede üç ayrı talep var; ortak bağlamı her soru için tekrar edin.",
    411: "Aynı olaydan doğan ayrı talepleri ayrı soru kutularına yazın ve ortak bağlamı koruyun.",
    414: "Soru kipi olan tek talebi bağlamıyla birlikte yakalayın.",
    402: "İki ayrı talebi ayrı soru kutularına yazın; Eurobond bağlamını her ikisinde de koruyun.",
    418: "Aynı belge içindeki üç talebi ayrı soru kutularına yazın ve ortak bağlamı koruyun.",
}


def get_active_questions(db: Session) -> list[QuizQuestion]:
    rows = db.execute(
        select(QuizQuestion).where(QuizQuestion.active.is_(True)).order_by(QuizQuestion.id.asc())
    ).scalars().all()
    return _unique_questions_by_text(rows)


def _unique_questions_by_text(questions: list[QuizQuestion]) -> list[QuizQuestion]:
    seen: set[str] = set()
    unique: list[QuizQuestion] = []
    for question in questions:
        key = _quiz_question_key(question.question_text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(question)
    return unique


def _quiz_question_key(text: str | None) -> str:
    return re.sub(r"\s+", " ", str(text or "").casefold()).strip()


def calculate_score(questions: list[QuizQuestion], answers: dict[int, str]) -> int:
    if not questions:
        return 0
    correct = 0
    qmap = {q.id: q for q in questions}
    for qid, chosen in answers.items():
        q = qmap.get(int(qid))
        if q and str(q.correct_option.value).upper() == str(chosen).upper():
            correct += 1
    return int(round((correct / len(questions)) * 100))


def grade_choice_answers(questions: list[QuizQuestion], answers: dict[int, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for question in questions:
        selected = str(answers.get(question.id, "") or "").upper() or None
        correct = question.correct_option.value.upper()
        rows.append(
            {
                "question_id": question.id,
                "question_text": question.question_text,
                "selected_option": selected,
                "selected_text": _option_text(question, selected),
                "correct_option": correct,
                "correct_text": _option_text(question, correct) or "",
                "correct": selected == correct,
                "explanation": question.explanation,
            }
        )
    return rows


def get_practical_questions(db: Session) -> list[dict[str, Any]]:
    labels = _load_practical_labels(db)
    out: list[dict[str, Any]] = []
    for label in labels:
        doc = label.document
        if not doc:
            continue
        out.append(
            {
                "training_label_id": label.id,
                "evrak_id": doc.evrak_id,
                "ozelge_metni": normalize_document_whitespace(doc.display_text),
                "expected_question_count": len(label.questions),
                "focus": PRACTICAL_QUIZ_FOCUS.get(label.id),
            }
        )
    return out


def submit_quiz(db: Session, user: User, answers: dict[int, str], practical_answers: list[dict[str, Any]] | None = None) -> dict:
    settings = get_settings()
    questions = get_active_questions(db)
    if not questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aktif sınav sorusu bulunamadı.")

    multiple_choice_score = calculate_score(questions, answers)
    choice_results = grade_choice_answers(questions, answers)
    practical_results = grade_practical_answers(db, practical_answers or [])
    practical_score = (
        int(round(sum(item["score"] for item in practical_results) / len(practical_results)))
        if practical_results
        else 100
    )
    score = int(round((multiple_choice_score + practical_score) / 2)) if practical_results else multiple_choice_score
    passed = score >= settings.quiz_passing_score
    first_pass = passed and not user.exam_passed
    details = {
        "multiple_choice_score": multiple_choice_score,
        "practical_score": practical_score if practical_results else None,
        "choice_results": choice_results,
        "practical_results": practical_results,
    }

    attempt = QuizAttempt(user_id=user.id, score=score, passed=passed, details_json=details)
    db.add(attempt)

    if first_pass:
        user.exam_passed = True
        user.exam_score = score
        user.exam_passed_at = datetime.now(timezone.utc)
        db.add(user)
    elif not passed:
        # sınav tekrarları için en son skoru saklamak istersek:
        user.exam_score = score
        db.add(user)

    db.commit()
    db.refresh(attempt)
    if first_pass:
        ensure_first_dragon_reward(db, user.id)

    return {
        "score": score,
        "multiple_choice_score": multiple_choice_score,
        "practical_score": practical_score if practical_results else None,
        "passed": passed,
        "passing_score": settings.quiz_passing_score,
        "attempted_at": attempt.attempted_at,
        "message": (
            "Tebrikler, sınavı geçtiniz."
            if passed
            else f"Sınavdan en az {settings.quiz_passing_score} puan almanız gerekmektedir."
        ),
        "choice_results": choice_results,
        "practical_results": practical_results,
    }


def get_user_quiz_attempts(db: Session, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    total_count = int(
        db.execute(select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == user_id)).scalar_one()
    )
    attempts = (
        db.execute(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.attempted_at.desc(), QuizAttempt.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    out: list[dict[str, Any]] = []
    for index, attempt in enumerate(attempts):
        details = attempt.details_json or {}
        out.append(
            {
                "id": attempt.id,
                "attempt_number": total_count - index,
                "score": attempt.score,
                "multiple_choice_score": details.get("multiple_choice_score"),
                "practical_score": details.get("practical_score"),
                "passed": attempt.passed,
                "attempted_at": attempt.attempted_at,
                "choice_results": details.get("choice_results") or [],
                "practical_results": details.get("practical_results") or [],
            }
        )
    return out


def _option_text(question: QuizQuestion, option: str | None) -> str | None:
    option_map = {
        "A": question.option_a,
        "B": question.option_b,
        "C": question.option_c,
        "D": question.option_d,
    }
    return option_map.get(str(option or "").upper())


def grade_practical_answers(db: Session, answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = {label.id: label for label in _load_practical_labels(db)}
    answer_map = {int(item.get("training_label_id")): item for item in answers if item.get("training_label_id")}
    results: list[dict[str, Any]] = []

    for label_id, label in labels.items():
        doc = label.document
        received_questions = [str(q or "") for q in answer_map.get(label_id, {}).get("questions", [])]
        expected_questions = [q.gold_question_text for q in sorted(label.questions, key=lambda q: q.question_order)]
        feedback: list[dict[str, Any]] = []
        question_scores: list[int] = []

        for index, expected in enumerate(expected_questions):
            received = received_questions[index] if index < len(received_questions) else ""
            comparison = _compare_question_text(expected, received)
            question_scores.append(comparison["score"])
            feedback.append(
                {
                    "field": f"Soru {index + 1}",
                    "correct": comparison["score"] == 100,
                    "message": comparison["message"],
                    "expected_preview": expected,
                    "received_preview": received,
                }
            )

        extra_questions = [q for q in received_questions[len(expected_questions) :] if q.strip()]
        for extra_index, extra in enumerate(extra_questions, start=len(expected_questions) + 1):
            question_scores.append(0)
            feedback.append(
                {
                    "field": f"Soru {extra_index}",
                    "correct": False,
                    "message": "Bu belge için beklenenden fazla soru girdiniz.",
                    "expected_preview": None,
                    "received_preview": extra,
                }
            )

        score = int(round(sum(question_scores) / len(question_scores))) if question_scores else 0
        results.append(
            {
                "training_label_id": label_id,
                "evrak_id": doc.evrak_id if doc else "",
                "correct": score == 100,
                "score": score,
                "feedback": feedback,
            }
        )

    return results


def _load_practical_labels(db: Session) -> list[TrainingLabel]:
    order = {label_id: idx for idx, label_id in enumerate(PRACTICAL_QUIZ_LABEL_IDS)}
    labels = (
        db.execute(
            select(TrainingLabel)
            .join(Document, TrainingLabel.document_id == Document.id)
            .where(TrainingLabel.id.in_(PRACTICAL_QUIZ_LABEL_IDS))
            .options(joinedload(TrainingLabel.document), joinedload(TrainingLabel.questions))
        )
        .unique()
        .scalars()
        .all()
    )
    return sorted(labels, key=lambda label: order.get(label.id, 999))


def _compare_question_text(expected: str, received: str) -> dict[str, Any]:
    expected_clean = _strip_outer_space(expected)
    received_clean = _strip_outer_space(received)

    if not received_clean:
        return {"score": 0, "message": "Bu soru boş bırakılmış."}
    if received_clean == expected_clean:
        return {"score": 100, "message": "Doğru. Soru metni beklenen metinle birebir eşleşiyor."}

    expected_flat = _collapse_space(expected_clean)
    received_flat = _collapse_space(received_clean)
    if expected_flat == received_flat:
        detail = _first_whitespace_difference(expected_clean, received_clean)
        return {
            "score": 85,
            "message": f"Metin doğru görünüyor ancak boşluk/satır sonu farkı var. {detail}",
        }

    similarity = _token_similarity(expected_flat, received_flat)
    if similarity >= 0.92:
        return {
            "score": 70,
            "message": "Soru büyük ölçüde doğru, ancak eksik/fazla kelime veya noktalama farkı var. Beklenen metinle karşılaştırın.",
        }
    if similarity >= 0.75:
        return {
            "score": 45,
            "message": "Soru kısmen doğru görünüyor ama bağlam veya talep kısmı eksik olabilir.",
        }
    return {"score": 0, "message": "Soru beklenen soru metniyle eşleşmiyor."}


def _strip_outer_space(value: str) -> str:
    return str(value or "").replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n").strip()


def _collapse_space(value: str) -> str:
    return re.sub(r"\s+", " ", _strip_outer_space(value)).strip()


def _first_whitespace_difference(expected: str, received: str) -> str:
    max_len = min(len(expected), len(received))
    for idx in range(max_len):
        if expected[idx] != received[idx]:
            if expected[idx].isspace() or received[idx].isspace():
                return f"İlk boşluk farkı yaklaşık {idx + 1}. karakterde."
            return f"İlk fark yaklaşık {idx + 1}. karakterde."
    if len(expected) != len(received):
        return "Metnin sonunda eksik/fazla boşluk veya satır sonu olabilir."
    return "Boşluk farkı tespit edildi."


def _token_similarity(expected: str, received: str) -> float:
    expected_tokens = expected.casefold().split()
    received_tokens = received.casefold().split()
    if not expected_tokens:
        return 0
    received_set = set(received_tokens)
    matched = sum(1 for token in expected_tokens if token in received_set)
    length_ratio = min(len(received_tokens), len(expected_tokens)) / max(len(received_tokens), len(expected_tokens), 1)
    return (matched / len(expected_tokens)) * length_ratio

