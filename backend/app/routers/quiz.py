from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.quiz import PracticalQuizQuestionOut, QuizAttemptOut, QuizQuestionOut, QuizSubmitRequest, QuizSubmitResponse
from app.services.quiz_service import get_active_questions, get_practical_questions, get_user_quiz_attempts, submit_quiz


router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.get("/questions", response_model=list[QuizQuestionOut])
def questions(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> list[QuizQuestionOut]:
    if current_user.exam_passed:
        return []
    qs = get_active_questions(db)
    return [QuizQuestionOut.model_validate(q) for q in qs]


@router.get("/practical-questions", response_model=list[PracticalQuizQuestionOut])
def practical_questions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PracticalQuizQuestionOut]:
    if current_user.exam_passed:
        return []
    rows = get_practical_questions(db)
    return [PracticalQuizQuestionOut(**row) for row in rows]


@router.get("/my-attempts", response_model=list[QuizAttemptOut])
def my_attempts(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> list[QuizAttemptOut]:
    rows = get_user_quiz_attempts(db, current_user.id)
    return [QuizAttemptOut(**row) for row in rows]


@router.post("/submit", response_model=QuizSubmitResponse)
def submit(payload: QuizSubmitRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> QuizSubmitResponse:
    result = submit_quiz(
        db,
        current_user,
        {int(k): v.value for k, v in payload.answers.items()},
        [item.model_dump() for item in payload.practical_answers],
    )
    return QuizSubmitResponse(**result)

