from __future__ import annotations

import pytest

from tests.conftest import ensure_no_daily, replace_daily_puzzle


@pytest.mark.asyncio
async def test_daily_returns_puzzle_without_solution_hash(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)

    response = await client.get("/api/puzzles/daily")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(puzzle.id)
    assert body["puzzle_type"] == "pattern"
    assert "content" in body
    assert "solution_hash" not in body
    assert "solution" not in body


@pytest.mark.asyncio
async def test_daily_404_when_missing(client, session, today_utc) -> None:
    await ensure_no_daily(session, today_utc)

    response = await client.get("/api/puzzles/daily")
    assert response.status_code == 404

    # restore a daily puzzle for other tests / local env
    await replace_daily_puzzle(session, today_utc, solution=9)
