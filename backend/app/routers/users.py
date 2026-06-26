from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.schemas.user import UserOut


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def my_profile(current_user=Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)

