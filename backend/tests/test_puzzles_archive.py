from __future__ import annotations

from datetime import timedelta

import pytest

from app.models import UserCompletion
from tests.conftest import (
    auth_header,
    cleanup_puzzle,
    cleanup_user,
    create_puzzle,
    create_user,
)


@pytest.mark.asyncio
async def test_archive_requires_auth(client) -> None:
    response = await client.get("/api/puzzles/archive/next")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_archive_returns_oldest_uncompleted(client, session, today_utc) -> None:
    user = await create_user(session)
    older = await create_puzzle(
        session,
        assigned=today_utc - timedelta(days=5),
        solution="I",
        content={
            "grid": [["A", "B", "C"], ["D", "E", "F"], ["G", "H", None]],
            "prompt": "letter?",
            "choices": ["I", "J", "K"],
        },
    )
    newer = await create_puzzle(
        session,
        assigned=today_utc - timedelta(days=3),
        solution=16,
        content={
            "grid": [[2, 4, 8], [3, 6, 12], [4, 8, None]],
            "prompt": "number?",
            "choices": [16, 14, 10],
        },
    )

    response = await client.get(
        "/api/puzzles/archive/next",
        headers=auth_header(user),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(older.id)
    assert "solution_hash" not in body
    assert "solution" not in body
    assert "explanation" not in body

    # complete oldest; next should be the newer past puzzle
    session.add(
        UserCompletion(
            user_id=user.id,
            puzzle_id=older.id,
            is_correct=True,
            score=100,
            time_taken_seconds=30,
            is_daily_official=False,
        )
    )
    await session.commit()

    response2 = await client.get(
        "/api/puzzles/archive/next",
        headers=auth_header(user),
    )
    assert response2.status_code == 200
    assert response2.json()["id"] == str(newer.id)

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, older.id)
    await cleanup_puzzle(session, newer.id)


@pytest.mark.asyncio
async def test_archive_404_when_all_completed(client, session, today_utc) -> None:
    user = await create_user(session)
    # Use a unique far-past date unlikely to collide with seed
    puzzle = await create_puzzle(
        session,
        assigned=today_utc - timedelta(days=90),
        solution=9,
    )
    session.add(
        UserCompletion(
            user_id=user.id,
            puzzle_id=puzzle.id,
            is_correct=True,
            score=100,
            time_taken_seconds=12,
            is_daily_official=False,
        )
    )
    await session.commit()

    # Mark all other historical puzzles completed for this user too
    from sqlalchemy import select
    from app.models import Puzzle

    historical = (
        await session.scalars(
            select(Puzzle).where(
                Puzzle.assigned_date.is_not(None),
                Puzzle.assigned_date < today_utc,
            )
        )
    ).all()
    for hist in historical:
        exists = await session.scalar(
            select(UserCompletion).where(
                UserCompletion.user_id == user.id,
                UserCompletion.puzzle_id == hist.id,
            )
        )
        if exists is None:
            session.add(
                UserCompletion(
                    user_id=user.id,
                    puzzle_id=hist.id,
                    is_correct=True,
                    score=100,
                    time_taken_seconds=50,
                    is_daily_official=False,
                )
            )
    await session.commit()

    response = await client.get(
        "/api/puzzles/archive/next",
        headers=auth_header(user),
    )
    assert response.status_code == 404

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)
