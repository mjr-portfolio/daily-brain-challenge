from datetime import UTC, date, datetime, timedelta

import pytest

from app.services.streak import apply_daily_result, display_streak
from tests.conftest import auth_header, cleanup_user, create_user


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
