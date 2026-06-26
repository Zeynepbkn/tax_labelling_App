from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.db.models.user import UserRole
from app.schemas.training import TrainingExampleOut, TrainingGuideOut
from app.services.training_service import get_training_examples, get_training_guide


router = APIRouter(prefix="/training", tags=["training"])


@router.get("/examples", response_model=list[TrainingExampleOut])
def examples(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> list[TrainingExampleOut]:
    ex = get_training_examples(db, limit=10)
    return [TrainingExampleOut(**e) for e in ex]


@router.get("/guide", response_model=TrainingGuideOut)
def guide(current_user=Depends(get_current_user)) -> TrainingGuideOut:
    g = get_training_guide(exam_passed=current_user.exam_passed or current_user.role == UserRole.admin)
    return TrainingGuideOut(**g)

