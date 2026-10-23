from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user_completion import UserCompletion


class User(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    streak_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    streak_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    best_streak: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    completions: Mapped[list[UserCompletion]] = relationship(
        back_populates="user",
    )
