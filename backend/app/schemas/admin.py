from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JsonUploadOut(BaseModel):
    id: int
    dataset_type: str
    filename: str
    content_type: str | None
    file_size_bytes: int
    sha256: str
    total_items: int
    added: int
    skipped: int
    duplicates: int
    warnings_count: int
    summary: dict | None = None
    uploaded_by_user_id: int | None
    uploaded_by_username: str | None = None
    created_at: datetime


class UploadDuplicateCheckOut(BaseModel):
    exists: bool
    matches: list[JsonUploadOut] = []


class UploadResult(BaseModel):
    added: int
    updated: int = 0
    converted: int = 0
    skipped: int
    duplicates: int
    warnings: list[str] = []
    upload: JsonUploadOut | None = None


class DashboardOut(BaseModel):
    total_users: int
    passed_users: int
    training_documents: int
    annotation_documents: int
    total_labeling_records: int
    today_labeling_records: int
    avg_completion_seconds: float | None = None
    top_labelers: list[dict]
    avg_labels_per_document: float | None = None


class PaginatedAdminRecordsOut(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int

