from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import PuzzleType, User, UserCompletion
from tests.conftest import (
    auth_header,
    cleanup_puzzle,
    cleanup_user,
    create_puzzle,
    create_puzzle_start,
    create_user,
    replace_daily_puzzle,
)


async def _completion(
    session,
    user: User,
    puzzle,
    *,
    correct: bool,
    score: int,
    seconds: int,
    official: bool = False,
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
async def test_stats_mix_types_and_empty_account(client, session, today_utc) -> None:
    user = await create_user(session)
    user.streak_count = 3
    user.streak_date = today_utc
    user.best_streak = 5
    await session.commit()

    pattern_a = await create_puzzle(session, assigned=today_utc - timedelta(days=4))
    pattern_b = await create_puzzle(session, assigned=today_utc - timedelta(days=5))
    anagram = await create_puzzle(
        session,
        assigned=today_utc - timedelta(days=2),
        puzzle_type=PuzzleType.ANAGRAM,
    )
    news = await create_puzzle(
        session,
        assigned=today_utc - timedelta(days=3),
        puzzle_type=PuzzleType.NEWS_QUIZ,
    )
    await _completion(session, user, pattern_a, correct=True, score=70, seconds=40, official=True)
    await _completion(session, user, pattern_b, correct=True, score=50, seconds=60)
    await _completion(session, user, anagram, correct=False, score=0, seconds=10)
    await _completion(session, user, news, correct=True, score=90, seconds=20)

    response = await client.get("/api/users/me/stats", headers=auth_header(user))
    assert response.status_code == 200
    body = response.json()
    assert body["current_streak"] == 3
    assert body["best_streak"] == 5
    overall = body["overall"]
    assert overall["puzzles_solved"] == 3
    assert overall["puzzles_played"] == 4
    assert overall["win_rate"] == 75.0
    assert overall["average_completion_time_seconds"] == 40.0
    pattern = overall["categories"]["pattern"]
    assert pattern["solved"] == 2
    assert pattern["played"] == 2
    assert pattern["available"] >= 2
    assert pattern["win_rate"] == 100.0
    assert pattern["average_completion_time_seconds"] == 50.0
    assert overall["puzzles_available"] >= 4
    opened = sum(
        min(overall["categories"][key]["played"], overall["categories"][key]["available"])
        for key in ("pattern", "anagram", "news_quiz")
    )
    assert overall["left_to_play"] == overall["puzzles_available"] - opened
    assert overall["completion_percent"] == round(
        100.0 * overall["puzzles_solved"] / overall["puzzles_available"], 1
    )
    assert overall["categories"]["anagram"]["solved"] == 0
    assert overall["categories"]["anagram"]["played"] == 1
    assert overall["categories"]["anagram"]["win_rate"] == 0.0
    assert overall["categories"]["anagram"]["average_completion_time_seconds"] is None
    assert overall["categories"]["news_quiz"]["solved"] == 1
    assert overall["categories"]["news_quiz"]["average_completion_time_seconds"] == 20.0
    daily = body["daily"]
    assert daily["puzzles_solved"] == 1
    assert daily["puzzles_played"] == 1
    assert daily["win_rate"] == 100.0
    assert daily["average_completion_time_seconds"] == 40.0
    assert daily["categories"]["pattern"]["solved"] == 1
    assert daily["categories"]["anagram"]["played"] == 0
    assert daily["categories"]["news_quiz"]["played"] == 0

    empty = await create_user(session)
    bare = await client.get("/api/users/me/stats", headers=auth_header(empty))
    assert bare.status_code == 200
    bare_body = bare.json()
    assert bare_body["current_streak"] == 0
    assert bare_body["best_streak"] == 0
    assert bare_body["overall"]["puzzles_played"] == 0
    assert bare_body["overall"]["left_to_play"] == bare_body["overall"]["puzzles_available"]
    assert bare_body["overall"]["win_rate"] is None
    assert bare_body["daily"]["puzzles_played"] == 0
    assert bare_body["daily"]["categories"]["pattern"]["played"] == 0

    guest = await client.get("/api/users/me/stats")
    assert guest.status_code == 401

    await cleanup_user(session, user.id)
    await cleanup_user(session, empty.id)
    for puzzle in (pattern_a, pattern_b, anagram, news):
        await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_best_streak_rises_and_survives_a_reset(client, session, today_utc) -> None:
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    user = await create_user(session)
    user.streak_count = 4
    user.streak_date = today_utc - timedelta(days=1)
    user.best_streak = 4
    await session.commit()
    await create_puzzle_start(session, user, puzzle, seconds_ago=12)

    continued = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 9, "time_taken_seconds": 12},
        headers=auth_header(user),
    )
    assert continued.status_code == 200
    assert continued.json()["streak"] == 5
    await session.refresh(user)
    assert user.streak_count == 5
    assert user.best_streak == 5

    stored = await session.scalar(
        select(UserCompletion).where(UserCompletion.user_id == user.id)
    )
    assert stored is not None
    await session.delete(stored)
    user.streak_count = 4
    user.streak_date = today_utc - timedelta(days=3)
    user.best_streak = 5
    await session.commit()

    reset = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 9, "time_taken_seconds": 12},
        headers=auth_header(user),
    )
    assert reset.status_code == 200
    assert reset.json()["streak"] == 1
    await session.refresh(user)
    assert user.streak_count == 1
    assert user.best_streak == 5

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_archive_submit_does_not_change_streaks(client, session, today_utc) -> None:
    archive = await create_puzzle(session, assigned=today_utc - timedelta(days=1), solution=9)
    user = await create_user(session)
    user.streak_count = 3
    user.streak_date = today_utc
    user.best_streak = 7
    await session.commit()

    response = await client.post(
        f"/api/puzzles/{archive.id}/submit",
        json={"answer": 9, "time_taken_seconds": 18},
        headers=auth_header(user),
    )
    assert response.status_code == 200
    assert response.json()["streak"] == 3
    assert response.json()["is_daily_official"] is False
    await session.refresh(user)
    assert user.streak_count == 3
    assert user.best_streak == 7

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, archive.id)
