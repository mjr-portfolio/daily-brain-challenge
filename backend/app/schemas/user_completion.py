from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AnswerType = int | str | list[int | str]


class CompletionCreate(BaseModel):
    answer: AnswerType
    time_taken_seconds: int = Field(ge=0)


class CompletionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    puzzle_id: UUID
    is_correct: bool
    score: int
    time_taken_seconds: int
    is_daily_official: bool
    completed_at: datetime


class SubmitResult(BaseModel):
    """Shared guest + auth response contract for the submit endpoint."""

    is_correct: bool
    time_taken_seconds: int
    correct_answer: AnswerType
    explanation: str
    percentile: float | None = None
    score: int | None = None
    is_daily_official: bool | None = None
