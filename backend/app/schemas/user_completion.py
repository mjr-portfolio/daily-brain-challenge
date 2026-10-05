from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompletionCreate(BaseModel):
    answer: Any
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
    """Shared guest + auth response contract for Phase 2 submit endpoint."""

    is_correct: bool
    time_taken_seconds: int
    percentile: float | None = None
    score: int | None = None
    is_daily_official: bool | None = None
