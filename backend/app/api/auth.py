from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.models.user import User
from app.models.user_completion import UserCompletion
from app.schemas.auth import AccountRead, StreakAdopt, TokenRequest, TokenResponse
from app.services.streak import display_streak

router = APIRouter(prefix="/auth", tags=["auth"])


def _today():
    return datetime.now(UTC).date()


async def _total_score(db: DbSession, user: User) -> int:
    total = await db.scalar(
        select(func.coalesce(func.sum(UserCompletion.score), 0)).where(
            UserCompletion.user_id == user.id
        )
    )
    return int(total or 0)


async def _account(db: DbSession, user: User, today) -> AccountRead:
    return AccountRead(
        email=user.email,
        streak=display_streak(user.streak_count, user.streak_date, today),
        total_score=await _total_score(db, user),
    )


@router.post("/token", response_model=TokenResponse)
async def issue_token(payload: TokenRequest, db: DbSession) -> TokenResponse:
    email = payload.email.lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=AccountRead)
async def read_account(db: DbSession, user: CurrentUser) -> AccountRead:
    return await _account(db, user, _today())


@router.post("/streak", response_model=AccountRead)
async def adopt_streak(payload: StreakAdopt, db: DbSession, user: CurrentUser) -> AccountRead:
    """Copy a guest streak onto an account that has never stored one."""
    today = _today()
    if user.streak_date is None and payload.last_date is not None:
        user.streak_count = display_streak(payload.count, payload.last_date, today)
        user.streak_date = payload.last_date
        user.best_streak = max(user.best_streak, user.streak_count)
        await db.commit()
    return await _account(db, user, today)
