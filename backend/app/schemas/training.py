from __future__ import annotations

from pydantic import BaseModel


class TrainingExampleOut(BaseModel):
    training_label_id: int | None = None
    evrak_id: str
    ozelge_metni: str
    gold_sorular: list[str]
    gold_cevap: str | None = None
    aciklama: str | None = None


class TrainingGuideOut(BaseModel):
    title: str
    content_markdown: str

