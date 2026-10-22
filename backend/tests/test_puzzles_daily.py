from __future__ import annotations

import pytest

from app.models import UserCompletion
from tests.conftest import (
    auth_header,
    cleanup_user,
    create_user,
    ensure_no_daily,
    replace_daily_puzzle,
)


@pytest.mark.asyncio
async def test_daily_returns_puzzle_without_solution_hash(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)

    response = await client.get("/api/puzzles/daily")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(puzzle.id)
    assert body["puzzle_type"] == "pattern"
    assert body["assigned_date"] == today_utc.isoformat()
    assert "content" not in body
    assert "solution_hash" not in body
    assert "solution" not in body
    assert "explanation" not in body
    assert body["is_completed"] is False
    assert body["started_at"] is None


@pytest.mark.asyncio
async def test_daily_completion_is_per_user(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    owner = await create_user(session)
    other = await create_user(session)
    session.add(
        UserCompletion(
            user_id=owner.id,
            puzzle_id=puzzle.id,
            is_correct=True,
            score=100,
            time_taken_seconds=8,
            is_daily_official=True,
        )
    )
    await session.commit()

    owner_response = await client.get("/api/puzzles/daily", headers=auth_header(owner))
    assert owner_response.status_code == 200
    assert owner_response.json()["is_completed"] is True

    other_response = await client.get("/api/puzzles/daily", headers=auth_header(other))
    assert other_response.status_code == 200
    assert other_response.json()["is_completed"] is False

    await cleanup_user(session, owner.id)
    await cleanup_user(session, other.id)
    await replace_daily_puzzle(session, today_utc, solution=9)


@pytest.mark.asyncio
async def test_daily_404_when_missing(client, session, today_utc) -> None:
    await ensure_no_daily(session, today_utc)

    response = await client.get("/api/puzzles/daily")
    assert response.status_code == 404

    # restore a daily puzzle for other tests / local env
    await replace_daily_puzzle(session, today_utc, solution=9)


@pytest.mark.asyncio
async def test_daily_start_returns_puzzle_and_keeps_original_time(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    user = await create_user(session)
    headers = auth_header(user)

    first = await client.post("/api/puzzles/daily/start", headers=headers)
    assert first.status_code == 200
    body = first.json()
    assert body["puzzle"]["id"] == str(puzzle.id)
    assert body["puzzle"]["content"]["choices"] == [9, 10, 12]
    assert "solution" not in body["puzzle"]
    assert "explanation" not in body["puzzle"]
    assert body["started_at"] is not None

    preview = await client.get("/api/puzzles/daily", headers=headers)
    assert preview.status_code == 200
    assert preview.json()["started_at"] == body["started_at"]
    assert "content" not in preview.json()

    second = await client.post("/api/puzzles/daily/start", headers=headers)
    assert second.status_code == 200
    assert second.json()["started_at"] == body["started_at"]

    await cleanup_user(session, user.id)
    await replace_daily_puzzle(session, today_utc, solution=9)


@pytest.mark.asyncio
async def test_guest_start_does_not_record_a_server_clock(client, session, today_utc) -> None:
    await replace_daily_puzzle(session, today_utc, solution=9)

    response = await client.post("/api/puzzles/daily/start")
    assert response.status_code == 200
    body = response.json()
    assert body["started_at"] is None
    assert "content" in body["puzzle"]
    assert "solution" not in body["puzzle"]

    preview = await client.get("/api/puzzles/daily")
    assert preview.json()["started_at"] is None
