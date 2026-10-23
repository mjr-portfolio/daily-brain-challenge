from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.models import User, UserCompletion
from tests.conftest import auth_header, cleanup_puzzle, cleanup_user, create_puzzle, create_user


async def _row(
    session,
    user: User,
    puzzle,
    *,
    seconds: int,
    score: int,
    official: bool,
    correct: bool = True,
) -> None:
    session.add(
        UserCompletion(
            user_id=user.id,
            puzzle_id=puzzle.id,
            is_correct=correct,
            score=score,
            time_taken_seconds=seconds,
            is_daily_official=official,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_benchmark_uses_official_solvers_only(client, session, today_utc) -> None:
    puzzle = await create_puzzle(session, assigned=today_utc - timedelta(days=1), solution=9)
    fast = await create_user(session)
    slow = await create_user(session)
    missed = await create_user(session)
    viewer = await create_user(session)
    viewer.streak_count = 4
    viewer.best_streak = 4
    viewer.streak_date = today_utc
    await session.commit()

    await _row(session, fast, puzzle, seconds=30, score=80, official=True)
    await _row(session, slow, puzzle, seconds=50, score=60, official=True)
    await _row(session, missed, puzzle, seconds=5, score=0, official=True, correct=False)
    await _row(session, viewer, puzzle, seconds=20, score=90, official=False)

    before = await session.scalar(select(func.count()).select_from(UserCompletion))
    response = await client.get(
        f"/api/puzzles/archive/{puzzle.id}/benchmark",
        headers=auth_header(viewer),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["solver_count"] == 2
    assert body["fastest_completion_time_seconds"] == 30
    assert body["median_completion_time_seconds"] == 40.0
    assert body["average_score"] == 70.0
    assert body["viewer"]["time_taken_seconds"] == 20
    assert body["viewer"]["score"] == 90
    assert body["viewer"]["faster_than_percent"] == 100.0

    after = await session.scalar(select(func.count()).select_from(UserCompletion))
    assert after == before
    await session.refresh(viewer)
    assert viewer.streak_count == 4
    assert viewer.best_streak == 4

    for user in (fast, slow, missed, viewer):
        await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_benchmark_tie_reports_zero_percent(client, session, today_utc) -> None:
    puzzle = await create_puzzle(session, assigned=today_utc - timedelta(days=2), solution=9)
    official = await create_user(session)
    viewer = await create_user(session)
    await _row(session, official, puzzle, seconds=30, score=100, official=True)
    await _row(session, viewer, puzzle, seconds=30, score=80, official=False)

    response = await client.get(
        f"/api/puzzles/archive/{puzzle.id}/benchmark",
        headers=auth_header(viewer),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fastest_completion_time_seconds"] == 30
    assert body["viewer"]["time_taken_seconds"] == 30
    assert body["viewer"]["faster_than_percent"] == 0.0

    await cleanup_user(session, official.id)
    await cleanup_user(session, viewer.id)
    await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_benchmark_rejects_live_puzzle_and_guests(client, session, today_utc) -> None:
    live = await create_puzzle(session, assigned=today_utc, solution=9)
    user = await create_user(session)

    guest = await client.get(f"/api/puzzles/archive/{live.id}/benchmark")
    assert guest.status_code == 401

    today = await client.get(
        f"/api/puzzles/archive/{live.id}/benchmark",
        headers=auth_header(user),
    )
    assert today.status_code == 404

    missing = await client.get(
        f"/api/puzzles/archive/{user.id}/benchmark",
        headers=auth_header(user),
    )
    assert missing.status_code == 404

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, live.id)
