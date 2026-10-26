from datetime import UTC, datetime, timedelta

import pytest

from app.models import UserCompletion
from tests.conftest import (
    auth_header,
    cleanup_puzzle,
    cleanup_user,
    create_user,
    ensure_no_daily,
    replace_daily_puzzle,
)


@pytest.mark.asyncio
async def test_leaderboard_orders_hides_email_and_ranks_viewer(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    faster = await create_user(session, email="faster-hidden@example.com", display_name="Faster")
    viewer = await create_user(session, email="viewer-hidden@example.com", display_name="Viewer")
    slower = await create_user(session, email="slower-hidden@example.com", display_name="Slower")
    unranked = await create_user(session, display_name="Unranked")
    base = datetime.now(UTC)
    session.add_all(
        [
            UserCompletion(
                user_id=slower.id,
                puzzle_id=puzzle.id,
                is_correct=True,
                score=90,
                time_taken_seconds=40,
                is_daily_official=True,
                completed_at=base,
            ),
            UserCompletion(
                user_id=faster.id,
                puzzle_id=puzzle.id,
                is_correct=True,
                score=90,
                time_taken_seconds=20,
                is_daily_official=True,
                completed_at=base + timedelta(seconds=1),
            ),
            UserCompletion(
                user_id=viewer.id,
                puzzle_id=puzzle.id,
                is_correct=False,
                score=0,
                time_taken_seconds=15,
                is_daily_official=True,
                completed_at=base + timedelta(seconds=2),
            ),
            UserCompletion(
                user_id=unranked.id,
                puzzle_id=puzzle.id,
                is_correct=True,
                score=100,
                time_taken_seconds=5,
                is_daily_official=False,
                completed_at=base,
            ),
        ]
    )
    await session.commit()

    guest = await client.get("/api/puzzles/daily/leaderboard")
    assert guest.status_code == 200
    guest_body = guest.json()
    assert guest_body["viewer"] is None
    assert [row["score"] for row in guest_body["entries"]] == [90, 90, 0]
    assert [row["completion_time_seconds"] for row in guest_body["entries"][:2]] == [20, 40]
    assert [row["rank"] for row in guest_body["entries"]] == [1, 2, 3]
    assert guest_body["entries"][0]["is_viewer"] is False
    payload = guest.text
    assert "faster-hidden@example.com" not in payload
    assert "viewer-hidden@example.com" not in payload
    assert [row["display_name"] for row in guest_body["entries"]] == ["Faster", "Slower", "Viewer"]
    assert all(not row["display_name"].startswith("Player #") for row in guest_body["entries"])

    mine = await client.get(
        "/api/puzzles/daily/leaderboard",
        headers=auth_header(viewer),
    )
    assert mine.status_code == 200
    body = mine.json()
    assert body["viewer"]["rank"] == 3
    assert body["viewer"]["is_viewer"] is True
    assert body["entries"][2]["is_viewer"] is True
    assert "viewer-hidden@example.com" not in mine.text

    rejected = await client.get("/api/puzzles/daily/leaderboard", params={"limit": 7})
    assert rejected.status_code == 422

    for user in (faster, viewer, slower, unranked):
        await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_leaderboard_viewer_outside_the_page(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    users = [await create_user(session) for _ in range(10)]
    viewer = await create_user(session)
    base = datetime.now(UTC)
    for index, user in enumerate(users):
        session.add(
            UserCompletion(
                user_id=user.id,
                puzzle_id=puzzle.id,
                is_correct=True,
                score=50,
                time_taken_seconds=index + 1,
                is_daily_official=True,
                completed_at=base + timedelta(seconds=index),
            )
        )
    session.add(
        UserCompletion(
            user_id=viewer.id,
            puzzle_id=puzzle.id,
            is_correct=True,
            score=10,
            time_taken_seconds=90,
            is_daily_official=True,
            completed_at=base + timedelta(minutes=1),
        )
    )
    await session.commit()

    response = await client.get(
        "/api/puzzles/daily/leaderboard",
        params={"limit": 10},
        headers=auth_header(viewer),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["entries"]) == 10
    assert all(row["is_viewer"] is False for row in body["entries"])
    assert body["viewer"]["rank"] == 11
    assert body["viewer"]["score"] == 10
    assert viewer.email not in response.text

    for user in (*users, viewer):
        await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_leaderboard_missing_daily_is_404(client, session, today_utc) -> None:
    await ensure_no_daily(session, today_utc)
    response = await client.get("/api/puzzles/daily/leaderboard")
    assert response.status_code == 404
