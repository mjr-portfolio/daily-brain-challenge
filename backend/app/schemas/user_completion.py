from pydantic import BaseModel, Field

from app.schemas.puzzle import ShapeItem

AnswerType = int | str | list[int | str] | ShapeItem


class CompletionCreate(BaseModel):
    answer: AnswerType
    time_taken_seconds: int = Field(ge=0)


class SubmitResult(BaseModel):
    """Shared guest + auth response contract for the submit endpoint."""

    is_correct: bool
    time_taken_seconds: int
    correct_answer: AnswerType
    explanation: str
    percentile: float | None = None
    score: int | None = None
    is_daily_official: bool | None = None
    streak: int | None = None
