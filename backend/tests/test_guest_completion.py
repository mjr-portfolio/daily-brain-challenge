"""Smoke tests for guest-capable UserCompletion rows."""

from __future__ import annotations

import hashlib
import json

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Puzzle, PuzzleType, User, UserCompletion

pytestmark = pytest.mark.asyncio


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
async def session() -> AsyncSession:
    if not await _db_available():
        pytest.skip("PostgreSQL is not available (start docker compose first)")

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        yield db
    await engine.dispose()


async def test_user_completions_user_id_nullable(session: AsyncSession) -> None:
    result = await session.execute(
        text(
            """
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_name = 'user_completions' AND column_name = 'user_id'
            """
        )
    )
    row = result.first()
    assert row is not None
    assert row[0] == "YES"


async def test_insert_guest_and_auth_completions(session: AsyncSession) -> None:
    solution = 9
    solution_hash = hashlib.sha256(
        json.dumps(solution, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    puzzle = Puzzle(
        puzzle_type=PuzzleType.PATTERN,
        assigned_date=None,
        content={
            "grid": [[1, 2], [3, None]],
            "prompt": "test",
            "choices": [4],
        },
        solution_hash=solution_hash,
        solution=solution,
        explanation="Each row increases by 1, so the blank is 9.",
    )
    user = User(email="phase1-test@example.com")
    session.add_all([puzzle, user])
    await session.flush()

    guest_completion = UserCompletion(
        user_id=None,
        puzzle_id=puzzle.id,
        is_correct=True,
        score=100,
        time_taken_seconds=42,
        is_daily_official=True,
    )
    auth_completion = UserCompletion(
        user_id=user.id,
        puzzle_id=puzzle.id,
        is_correct=True,
        score=100,
        time_taken_seconds=30,
        is_daily_official=True,
    )
    session.add_all([guest_completion, auth_completion])
    await session.commit()

    rows = (
        await session.scalars(
            select(UserCompletion).where(UserCompletion.puzzle_id == puzzle.id)
        )
    ).all()
    assert len(rows) == 2
    assert any(row.user_id is None for row in rows)
    assert any(row.user_id == user.id for row in rows)

    # cleanup test rows
    await session.delete(guest_completion)
    await session.delete(auth_completion)
    await session.delete(puzzle)
    await session.delete(user)
    await session.commit()
