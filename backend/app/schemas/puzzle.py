from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.puzzle import PuzzleType


class PatternContent(BaseModel):
    grid: list[list[str | int | None]]
    prompt: str
    choices: list[str | int] | None = None


class AnagramContent(BaseModel):
    scrambled_word: str
    hint: str | None = None
    prompt: str | None = "Unscramble the letters to reveal the target word"


class NewsQuizContent(BaseModel):
    question: str
    options: list[str]
    source_headline: str | None = None
    hint: str | None = None


class PuzzleCreate(BaseModel):
    puzzle_type: PuzzleType
    assigned_date: date | None = None
    content: dict[str, Any]
    solution_hash: str


class PuzzleReadBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assigned_date: date | None
    created_at: datetime


class PatternPuzzleRead(PuzzleReadBase):
    puzzle_type: Literal[PuzzleType.PATTERN] = PuzzleType.PATTERN
    content: PatternContent


class AnagramPuzzleRead(PuzzleReadBase):
    puzzle_type: Literal[PuzzleType.ANAGRAM] = PuzzleType.ANAGRAM
    content: AnagramContent


class NewsQuizPuzzleRead(PuzzleReadBase):
    puzzle_type: Literal[PuzzleType.NEWS_QUIZ] = PuzzleType.NEWS_QUIZ
    content: NewsQuizContent


PuzzleRead = Annotated[
    PatternPuzzleRead | AnagramPuzzleRead | NewsQuizPuzzleRead,
    Field(discriminator="puzzle_type"),
]
