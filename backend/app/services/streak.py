"""Daily streak: any submit continues yesterday's run, and a missed day clears it."""

from datetime import date, timedelta


def display_streak(count: int, streak_date: date | None, today: date) -> int:
    if streak_date is None:
        return 0
    if streak_date < today - timedelta(days=1):
        return 0
    return max(0, count)


def apply_daily_result(
    count: int,
    streak_date: date | None,
    today: date,
) -> tuple[int, date]:
    """Return the stored count and the day this result settles."""
    if streak_date == today:
        return display_streak(count, streak_date, today), today

    visible = display_streak(count, streak_date, today)
    yesterday = today - timedelta(days=1)
    if streak_date == yesterday and visible > 0:
        return visible + 1, today
    return 1, today
