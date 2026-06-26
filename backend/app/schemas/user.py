from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.db.models.user import UserRole


class UserOut(BaseModel):
    id: int
    kullanici_adi: str
    email: EmailStr
    role: UserRole
    exam_passed: bool
    exam_score: int | None
    exam_passed_at: datetime | None
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class AdminUserStatsOut(UserOut):
    completed_documents: int = 0
    avg_duration_seconds: float | None = None

