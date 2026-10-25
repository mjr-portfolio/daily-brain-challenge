import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.cookies import REFRESH_COOKIE, attach_session, clear_auth_cookies
from app.core.deps import CurrentUser, DbSession
from app.core.passwords import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    AccountRead,
    LoginRequest,
    RegisterRequest,
    StreakAdopt,
    StreakAdoptResult,
)
from app.services.accounts import (
    account_read,
    clear_session,
    display_name_taken,
    start_session,
)
from app.services.streak import display_streak

router = APIRouter(prefix="/auth", tags=["auth"])


def _today():
    return datetime.now(UTC).date()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/register", response_model=AccountRead)
async def register(payload: RegisterRequest, response: Response, db: DbSession) -> AccountRead:
    email = payload.email.lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is not None and user.password_hash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    if payload.display_name and await display_name_taken(
        db,
        payload.display_name,
        exclude_user_id=None if user is None else user.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That display name is already taken",
        )

    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
        )
        db.add(user)
    else:
        user.password_hash = hash_password(payload.password)
        if payload.display_name is not None:
            user.display_name = payload.display_name

    try:
        await db.flush()
        tokens = start_session(user)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or display name already exists",
        ) from exc
    attach_session(response, tokens)
    return await account_read(db, user, _today())


@router.post("/login", response_model=AccountRead)
async def login(payload: LoginRequest, response: Response, db: DbSession) -> AccountRead:
    email = payload.email.lower()
    user = await db.scalar(select(User).where(User.email == email))
    if (
        user is None
        or user.password_hash is None
        or not verify_password(payload.password, user.password_hash)
    ):
        raise _unauthorized("Invalid email or password")

    tokens = start_session(user)
    await db.commit()
    attach_session(response, tokens)
    return await account_read(db, user, _today())


@router.post("/refresh")
async def refresh(request: Request, db: DbSession) -> JSONResponse:
    raw = request.cookies.get(REFRESH_COOKIE)
    user = None
    if raw:
        digest = hashlib.sha256(raw.encode()).hexdigest()
        user = await db.scalar(select(User).where(User.refresh_token_hash == digest))
    now = datetime.now(UTC)
    expires = None if user is None else user.refresh_token_expires_at
    if user is None or expires is None or expires <= now:
        if user is not None:
            clear_session(user)
            await db.commit()
        body = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or expired token"},
        )
        clear_auth_cookies(body)
        return body

    tokens = start_session(user)
    await db.commit()
    account = await account_read(db, user, _today())
    body = JSONResponse(content=jsonable_encoder(account))
    attach_session(body, tokens)
    return body


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(db: DbSession, user: CurrentUser) -> Response:
    clear_session(user)
    await db.commit()
    outgoing = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(outgoing)
    return outgoing


@router.get("/me", response_model=AccountRead)
async def read_account(db: DbSession, user: CurrentUser) -> AccountRead:
    return await account_read(db, user, _today())


@router.post("/streak", response_model=StreakAdoptResult)
async def adopt_streak(payload: StreakAdopt, db: DbSession, user: CurrentUser) -> StreakAdoptResult:
    """Copy a guest streak onto an account that has never stored one."""
    today = _today()
    applied = False
    if user.streak_date is None and payload.last_date is not None:
        user.streak_count = display_streak(payload.count, payload.last_date, today)
        user.streak_date = payload.last_date
        user.best_streak = max(user.best_streak, user.streak_count)
        applied = True
        await db.commit()
    account = await account_read(db, user, today)
    return StreakAdoptResult(**account.model_dump(), applied=applied)
