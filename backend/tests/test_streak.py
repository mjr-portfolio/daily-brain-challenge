from datetime import UTC, date, datetime, timedelta

import pytest

from app.models import UserCompletion
from app.services.streak import apply_daily_result, display_streak
from tests.conftest import auth_header, cleanup_puzzle, cleanup_user, create_puzzle, create_user


def test_display_streak_drops_after_a_missed_day() -> None:
    today = date(2026, 10, 21)
    assert display_streak(4, today - timedelta(days=2), today) == 0
    assert display_streak(4, today - timedelta(days=1), today) == 4
    assert display_streak(4, today, today) == 4
    assert display_streak(0, None, today) == 0


def test_daily_submit_continues_or_starts() -> None:
    today = date(2026, 10, 21)
    yesterday = today - timedelta(days=1)
    assert apply_daily_result(4, yesterday, today) == (5, today)
    assert apply_daily_result(0, None, today) == (1, today)
    assert apply_daily_result(4, today - timedelta(days=3), today) == (1, today)


def test_second_result_today_does_not_increment_again() -> None:
    today = date(2026, 10, 21)
    assert apply_daily_result(5, today, today) == (5, today)


def test_incorrect_daily_still_counts_as_played() -> None:
    today = date(2026, 10, 21)
    yesterday = today - timedelta(days=1)
    assert apply_daily_result(4, yesterday, today) == (5, today)


@pytest.mark.asyncio
async def test_adopt_streak_keeps_an_existing_account_streak(client, session) -> None:
    user = await create_user(session)
    headers = auth_header(user)
    today = datetime.now(UTC).date().isoformat()

    first = await client.post(
        "/api/auth/streak",
        json={"count": 4, "last_date": today},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["streak"] == 4

    second = await client.post(
        "/api/auth/streak",
        json={"count": 9, "last_date": today},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["streak"] == 4

    account = await client.get("/api/auth/me", headers=headers)
    assert account.status_code == 200
    assert account.json()["streak"] == 4

    await cleanup_user(session, user.id)


@pytest.mark.asyncio
async def test_account_total_score_sums_every_completion(client, session) -> None:
    user = await create_user(session)
    solved = await create_puzzle(session, assigned=None, solution=9)
    incorrect = await create_puzzle(session, assigned=None, solution=4)
    session.add_all(
        [
            UserCompletion(
                user_id=user.id,
                puzzle_id=solved.id,
                is_correct=True,
                score=80,
                time_taken_seconds=30,
                is_daily_official=False,
            ),
            UserCompletion(
                user_id=user.id,
                puzzle_id=incorrect.id,
                is_correct=False,
                score=0,
                time_taken_seconds=12,
                is_daily_official=False,
            ),
        ]
    )
    await session.commit()

    response = await client.get("/api/auth/me", headers=auth_header(user))
    assert response.status_code == 200
    assert response.json()["total_score"] == 80

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, solved.id)
    await cleanup_puzzle(session, incorrect.id)
