from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user_completion import UserCompletion


class PuzzleType(str, enum.Enum):
    PATTERN = "pattern"
    ANAGRAM = "anagram"
    NEWS_QUIZ = "news_quiz"


class Puzzle(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "puzzles"

    puzzle_type: Mapped[PuzzleType] = mapped_column(
        Enum(PuzzleType, name="puzzle_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    assigned_date: Mapped[date | None] = mapped_column(Date, unique=True, nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    solution_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    solution: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    completions: Mapped[list[UserCompletion]] = relationship(
        back_populates="puzzle",
    )
