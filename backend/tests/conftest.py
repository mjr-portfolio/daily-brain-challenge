from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Puzzle, PuzzleType, User, UserCompletion
from app.services.hashing import hash_solution


async def _db_available() -> bool:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def engine():
    if not await _db_available():
        pytest.skip("PostgreSQL is not available (start docker compose first)")
    settings = get_settings()
    eng = create_async_engine(settings.DATABASE_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        yield db


@pytest_asyncio.fixture
async def client(engine) -> AsyncIterator[AsyncClient]:
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def today_utc() -> date:
    return datetime.now(UTC).date()


async def create_user(session: AsyncSession, email: str | None = None) -> User:
    user = User(email=email or f"user-{uuid4().hex}@example.com")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def create_puzzle(
    session: AsyncSession,
    *,
    assigned: date | None,
    solution: object = 9,
    explanation: str = "Each row increases by 1, so the blank is 9.",
    content: dict | None = None,
) -> Puzzle:
    puzzle = Puzzle(
        puzzle_type=PuzzleType.PATTERN,
        assigned_date=assigned,
        content=content
        or {
            "grid": [[1, 2, 3], [4, 5, 6], [7, 8, None]],
            "prompt": "Which number completes the sequence?",
            "choices": [9, 10, 12],
        },
        solution_hash=hash_solution(solution),
        solution=solution,
        explanation=explanation,
    )
    session.add(puzzle)
    await session.commit()
    await session.refresh(puzzle)
    return puzzle


async def cleanup_puzzle(session: AsyncSession, puzzle_id) -> None:
    await session.execute(
        delete(UserCompletion).where(UserCompletion.puzzle_id == puzzle_id)
    )
    await session.execute(delete(Puzzle).where(Puzzle.id == puzzle_id))
    await session.commit()


async def cleanup_user(session: AsyncSession, user_id) -> None:
    await session.execute(delete(UserCompletion).where(UserCompletion.user_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))
    await session.commit()


async def replace_daily_puzzle(
    session: AsyncSession,
    today: date,
    *,
    solution: object = 9,
) -> Puzzle:
    existing = await session.scalar(select(Puzzle).where(Puzzle.assigned_date == today))
    if existing is not None:
        await cleanup_puzzle(session, existing.id)
    return await create_puzzle(session, assigned=today, solution=solution)


async def ensure_no_daily(session: AsyncSession, today: date) -> list:
    """Temporarily remove today's puzzle; return removed puzzle ids for restore helpers."""
    existing = await session.scalar(select(Puzzle).where(Puzzle.assigned_date == today))
    if existing is None:
        return []
    puzzle_id = existing.id
    await cleanup_puzzle(session, puzzle_id)
    return [puzzle_id]
