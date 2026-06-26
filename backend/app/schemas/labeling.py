from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LabelingSubmitRequest(BaseModel):
    document_id: int
    questions: list[str] = Field(min_length=1)
    cevap: str = Field(min_length=1)
    belgeyi_tamamlama_suresi: int | None = None  # saniye
    force_submit: bool = False


class LabelingUpdateRequest(BaseModel):
    """Mevcut etiketleme kaydını güncelle (aynı doğrulamalar submit ile)."""

    questions: list[str] = Field(min_length=1)
    cevap: str = Field(min_length=1)
    belgeyi_tamamlama_suresi: int | None = None  # saniye
    force_submit: bool = False


class LabelingSubmitWarnings(BaseModel):
    warnings: list[str]


class LabelingSubmitResponse(BaseModel):
    record_id: int
    message: str
    warnings: list[str] = []


class DailyProgressOut(BaseModel):
    date: str
    count: int


class DragonRewardOut(BaseModel):
    id: int
    reward_date: str
    milestone: int = 0
    color: str
    name: str
    created_at: datetime


class MotivationOut(BaseModel):
    kind: str
    title: str
    message: str


class MyProgressOut(BaseModel):
    completed_count: int
    today_completed_count: int
    yesterday_completed_count: int
    improvement_delta: int
    total_score: int = 0
    best_daily_count: int
    previous_best_daily_count: int
    daily_counts: list[DailyProgressOut]
    motivation_messages: list[MotivationOut]
    dragon_rewards: list[DragonRewardOut]
    dragon_awarded_today: bool = False
    avg_duration_seconds: float | None = None


class LeaderboardEntryOut(BaseModel):
    rank: int
    user_id: int
    kullanici_adi: str
    total_score: int = 0
    completed_count: int
    today_completed_count: int
    avg_duration_seconds: float | None = None
    dragon_count: int = 0
    is_current_user: bool = False


class LeaderboardOut(BaseModel):
    entries: list[LeaderboardEntryOut]
    current_user: LeaderboardEntryOut | None = None


class LabelingQuestionOut(BaseModel):
    question_order: int
    question_text: str
    character_count: int

    model_config = {"from_attributes": True}


class LabelingRecordSummaryOut(BaseModel):
    id: int
    document_id: int
    evrak_id: str
    soru_sayisi: int
    belgeyi_tamamlama_suresi_seconds: int | None = None
    belge_tamamlama_tarihi: datetime | None = None
    created_at: datetime


class PaginatedLabelingRecordSummaryOut(BaseModel):
    items: list[LabelingRecordSummaryOut]
    total: int
    page: int
    page_size: int


class LabelingRecordOut(BaseModel):
    id: int
    document_id: int
    evrak_id: str
    soru_sayisi: int
    cevap: str
    belgeyi_tamamlama_suresi_seconds: int | None = None
    belge_tamamlama_tarihi: datetime | None = None
    created_at: datetime
    questions: list[LabelingQuestionOut]

