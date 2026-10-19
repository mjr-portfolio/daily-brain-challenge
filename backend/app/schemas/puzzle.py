from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.puzzle import PuzzleType


class ShapeItem(BaseModel):
    shape: Literal["circle", "triangle", "square", "diamond", "star", "pentagon", "hexagon"]
    color: Literal["red", "blue", "green", "purple", "yellow", "orange"]
    rotation: int = 0
    count: int = Field(default=1, ge=1, le=4)

    @field_validator("rotation", mode="before")
    @classmethod
    def default_rotation(cls, value: object) -> object:
        if value is None:
            return 0
        return value

    @field_validator("rotation")
    @classmethod
    def check_rotation(cls, value: int) -> int:
        if value not in (0, 90, 180, 270):
            raise ValueError("rotation must be 0, 90, 180, or 270")
        return value

    @field_validator("count", mode="before")
    @classmethod
    def default_count(cls, value: object) -> object:
        if value is None:
            return 1
        return value


PatternElement = str | ShapeItem


class PatternContent(BaseModel):
    grid: list[list[str | int | ShapeItem | None]]
    prompt: str
    choices: list[str | int | ShapeItem] | None = None


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
