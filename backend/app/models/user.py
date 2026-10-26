from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, DateTime, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user_completion import UserCompletion


class User(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(32), nullable=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    refresh_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
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


Index(
    "uq_users_display_name_lower",
    func.lower(User.display_name),
    unique=True,
)
