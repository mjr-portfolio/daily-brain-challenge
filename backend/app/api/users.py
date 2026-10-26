from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.cookies import attach_session, clear_auth_cookies
from app.core.deps import CurrentUser, DbSession
from app.core.passwords import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AccountRead
from app.schemas.profile import DeleteAccount, UserUpdate
from app.schemas.stats import UserStatsRead
from app.services.accounts import account_read, display_name_taken, start_session
from app.services.stats import user_stats

router = APIRouter(prefix="/users", tags=["users"])


def _today():
    return datetime.now(UTC).date()


def _password_matches(user: User, password: str | None) -> bool:
    return bool(
        password
        and user.password_hash
        and verify_password(password, user.password_hash)
    )


@router.get("/me/stats", response_model=UserStatsRead)
async def read_my_stats(db: DbSession, user: CurrentUser) -> UserStatsRead:
    return await user_stats(db, user, _today())


@router.patch("/me", response_model=AccountRead)
async def update_me(
    payload: UserUpdate,
    response: Response,
    db: DbSession,
    user: CurrentUser,
) -> AccountRead:
    next_email = user.email
    email_changing = False
    if "email" in payload.model_fields_set and payload.email is not None:
        next_email = payload.email.lower()
        email_changing = next_email != user.email

    password_changing = payload.new_password is not None
    if email_changing or password_changing:
        if not payload.current_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Current password is required",
            )
        if not _password_matches(user, payload.current_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )

    if email_changing:
        taken = await db.scalar(select(User.id).where(User.email == next_email))
        if taken is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        user.email = next_email

    if "display_name" in payload.model_fields_set:
        name = payload.display_name
        if name is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Display name is required",
            )
        if await display_name_taken(db, name, exclude_user_id=user.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That display name is already taken",
            )
        user.display_name = name

    if payload.theme is not None:
        stored = dict(user.preferences or {})
        stored["theme"] = payload.theme
        user.preferences = stored

    tokens = None
    if password_changing and payload.new_password is not None:
        user.password_hash = hash_password(payload.new_password)
        tokens = start_session(user)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or display name already exists",
        ) from exc

    if tokens is not None:
        attach_session(response, tokens)
    return await account_read(db, user, _today())


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(payload: DeleteAccount, db: DbSession, user: CurrentUser) -> Response:
    if not _password_matches(user, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await db.delete(user)
    await db.commit()
    outgoing = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(outgoing)
    return outgoing
