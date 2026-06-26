from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models.quiz import QuizOption


class QuizQuestionOut(BaseModel):
    id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str

    model_config = {"from_attributes": True}


class AdminQuizQuestionOut(QuizQuestionOut):
    correct_option: QuizOption
    explanation: str | None = None
    active: bool


class QuizQuestionUpsert(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: QuizOption
    explanation: str | None = None
    active: bool = True


class QuizSubmitRequest(BaseModel):
    # question_id -> seçilen şık
    answers: dict[int, QuizOption]
    practical_answers: list["PracticalQuizAnswerIn"] = Field(default_factory=list)


class QuizSubmitResponse(BaseModel):
    score: int
    multiple_choice_score: int | None = None
    practical_score: int | None = None
    passed: bool
    passing_score: int = Field(default=75)
    message: str
    attempted_at: datetime
    choice_results: list["QuizChoiceResultOut"] = Field(default_factory=list)
    practical_results: list["PracticalQuizResultOut"] = Field(default_factory=list)


class QuizAttemptOut(BaseModel):
    id: int
    attempt_number: int
    score: int
    multiple_choice_score: int | None = None
    practical_score: int | None = None
    passed: bool
    attempted_at: datetime
    choice_results: list["QuizChoiceResultOut"] = Field(default_factory=list)
    practical_results: list["PracticalQuizResultOut"] = Field(default_factory=list)


class QuizChoiceResultOut(BaseModel):
    question_id: int
    question_text: str
    selected_option: str | None = None
    selected_text: str | None = None
    correct_option: str
    correct_text: str
    correct: bool
    explanation: str | None = None


class PracticalQuizQuestionOut(BaseModel):
    training_label_id: int
    evrak_id: str
    ozelge_metni: str
    expected_question_count: int
    focus: str | None = None


class PracticalQuizAnswerIn(BaseModel):
    training_label_id: int
    questions: list[str] = Field(default_factory=list)


class PracticalFieldFeedbackOut(BaseModel):
    field: str
    correct: bool
    message: str
    expected_preview: str | None = None
    received_preview: str | None = None


class PracticalQuizResultOut(BaseModel):
    training_label_id: int
    evrak_id: str
    correct: bool
    score: int
    feedback: list[PracticalFieldFeedbackOut]

