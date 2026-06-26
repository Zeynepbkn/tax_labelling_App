"""
Şema isim taslakları (bu adımda kod üretmiyoruz, sadece planlıyoruz).

Önerilen Pydantic şemaları:
- Auth:
  - Token
  - TokenPayload
  - LoginRequest
  - RegisterRequest
- Users:
  - UserCreate
  - UserUpdate
  - UserOut
  - AdminUserUpdate
- Documents:
  - DocumentOut
  - DocumentIngestItem (JSON import satırı)
  - DocumentIngestResult
- Training:
  - TrainingExampleOut
  - TrainingLabelOut
  - TrainingLabelQuestionOut
- Quiz:
  - QuizQuestionOut
  - QuizSubmitRequest
  - QuizAttemptOut
- Labeling:
  - LabelingRecordCreate
  - LabelingRecordOut
  - LabelingQuestionCreate
  - LabelingQuestionOut
- Export/Dashboard:
  - ExportRowOut
  - DashboardStatsOut
"""

