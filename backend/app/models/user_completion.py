from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.puzzle import Puzzle
    from app.models.user import User


class UserCompletion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "user_completions"
    __table_args__ = (
        Index(
            "ix_user_completions_percentile",
            "puzzle_id",
            "is_daily_official",
            "time_taken_seconds",
        ),
        Index(
            "uq_user_completions_user_puzzle",
            "user_id",
            "puzzle_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    puzzle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("puzzles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    is_daily_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User | None] = relationship(back_populates="completions")
    puzzle: Mapped[Puzzle] = relationship(back_populates="completions")
