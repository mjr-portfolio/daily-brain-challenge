"""Account reads and the single refresh session stored on the user row."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, make_refresh_token
from app.models.user import User
from app.models.user_completion import UserCompletion
from app.schemas.auth import AccountRead, TokenResponse
from app.schemas.profile import PreferencesRead
from app.services.streak import display_streak


def preferences_of(user: User) -> PreferencesRead:
    raw: Any = user.preferences if isinstance(user.preferences, dict) else {}
    theme = raw.get("theme") if isinstance(raw, dict) else None
    if theme not in ("dark", "light"):
        theme = "dark"
    return PreferencesRead(theme=theme)


async def total_score(db: AsyncSession, user: User) -> int:
    total = await db.scalar(
        select(func.coalesce(func.sum(UserCompletion.score), 0)).where(
            UserCompletion.user_id == user.id
        )
    )
    return int(total or 0)


async def account_read(db: AsyncSession, user: User, today: date) -> AccountRead:
    return AccountRead(
        email=user.email,
        display_name=user.display_name,
        preferences=preferences_of(user),
        streak=display_streak(user.streak_count, user.streak_date, today),
        total_score=await total_score(db, user),
    )


async def display_name_taken(
    db: AsyncSession,
    name: str,
    *,
    exclude_user_id: UUID | None = None,
) -> bool:
    stmt = select(User.id).where(func.lower(User.display_name) == name.lower())
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    return await db.scalar(stmt) is not None


def start_session(user: User) -> TokenResponse:
    raw, digest, expires = make_refresh_token()
    user.refresh_token_hash = digest
    user.refresh_token_expires_at = expires
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=raw,
    )


def clear_session(user: User) -> None:
    user.refresh_token_hash = None
    user.refresh_token_expires_at = None
