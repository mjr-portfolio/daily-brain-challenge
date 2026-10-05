from __future__ import annotations

from sqlalchemy import func, select

import pytest

from app.models import UserCompletion
from tests.conftest import (
    auth_header,
    cleanup_puzzle,
    cleanup_user,
    create_user,
    replace_daily_puzzle,
)


@pytest.mark.asyncio
async def test_guest_correct_no_persistence(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    before = await session.scalar(select(func.count()).select_from(UserCompletion))

    response = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 9, "time_taken_seconds": 42},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is True
    assert body["time_taken_seconds"] == 42
    assert body["percentile"] is None
    assert body["score"] is None
    assert body["correct_answer"] == 9
    assert body["explanation"] == "Each row increases by 1, so the blank is 9."

    after = await session.scalar(select(func.count()).select_from(UserCompletion))
    assert after == before


@pytest.mark.asyncio
async def test_guest_incorrect_no_persistence(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    before = await session.scalar(select(func.count()).select_from(UserCompletion))

    response = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 12, "time_taken_seconds": 15},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is False
    assert body["percentile"] is None
    assert body["correct_answer"] == 9
    assert isinstance(body["explanation"], str)

    after = await session.scalar(select(func.count()).select_from(UserCompletion))
    assert after == before


@pytest.mark.asyncio
async def test_auth_correct_official_persists_and_percentile(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    user = await create_user(session)

    response = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 9, "time_taken_seconds": 25},
        headers=auth_header(user),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is True
    assert body["is_daily_official"] is True
    assert body["score"] == 100
    assert isinstance(body["percentile"], float)
    assert body["percentile"] == 100.0
    assert body["correct_answer"] == 9
    assert body["explanation"]

    row = await session.scalar(
        select(UserCompletion).where(
            UserCompletion.user_id == user.id,
            UserCompletion.puzzle_id == puzzle.id,
        )
    )
    assert row is not None
    assert row.is_correct is True

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)
    await replace_daily_puzzle(session, today_utc, solution=9)


@pytest.mark.asyncio
async def test_auth_incorrect_persists_without_percentile(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    user = await create_user(session)

    response = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 10, "time_taken_seconds": 40},
        headers=auth_header(user),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is False
    assert body["score"] == 0
    assert body["percentile"] is None
    assert body["is_daily_official"] is True
    assert body["correct_answer"] == 9
    assert body["explanation"]

    row = await session.scalar(
        select(UserCompletion).where(
            UserCompletion.user_id == user.id,
            UserCompletion.puzzle_id == puzzle.id,
        )
    )
    assert row is not None
    assert row.is_correct is False

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)
    await replace_daily_puzzle(session, today_utc, solution=9)


@pytest.mark.asyncio
async def test_auth_duplicate_submit_conflict(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    user = await create_user(session)
    headers = auth_header(user)

    first = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 9, "time_taken_seconds": 20},
        headers=headers,
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 9, "time_taken_seconds": 18},
        headers=headers,
    )
    assert second.status_code == 409

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)
    await replace_daily_puzzle(session, today_utc, solution=9)


@pytest.mark.asyncio
async def test_invalid_bearer_returns_401(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)

    response = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 9, "time_taken_seconds": 20},
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401
