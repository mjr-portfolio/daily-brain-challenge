"""Lifetime stats from stored completions. Streak fields stay on the user row."""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.puzzle import Puzzle, PuzzleType
from app.models.user import User
from app.models.user_completion import UserCompletion
from app.schemas.stats import CategoryBreakdown, CategoryStats, StatsSlice, UserStatsRead
from app.services.streak import display_streak

_CATEGORY_TYPES = (PuzzleType.PATTERN, PuzzleType.ANAGRAM, PuzzleType.NEWS_QUIZ)


def _percent(solved: int, played: int) -> float | None:
    if played == 0:
        return None
    return round(100.0 * solved / played, 1)


def _average(time_sum: int, solved: int) -> float | None:
    if solved == 0:
        return None
    return round(time_sum / solved, 1)


def _empty_category() -> CategoryStats:
    return CategoryStats(
        solved=0,
        played=0,
        available=0,
        win_rate=None,
        average_completion_time_seconds=None,
    )


def _slice(
    totals: dict[PuzzleType, tuple[int, int, int]],
    available: dict[PuzzleType, int] | None = None,
) -> StatsSlice:
    catalog = available or {}
    buckets = {puzzle_type: _empty_category() for puzzle_type in _CATEGORY_TYPES}
    solved = 0
    played = 0
    time_sum = 0
    for puzzle_type, (row_played, row_solved, row_time) in totals.items():
        played += row_played
        solved += row_solved
        time_sum += row_time
        if puzzle_type in buckets:
            buckets[puzzle_type] = CategoryStats(
                solved=row_solved,
                played=row_played,
                available=catalog.get(puzzle_type, 0),
                win_rate=_percent(row_solved, row_played),
                average_completion_time_seconds=_average(row_time, row_solved),
            )
    for puzzle_type, released in catalog.items():
        if puzzle_type in buckets and puzzle_type not in totals:
            buckets[puzzle_type] = CategoryStats(
                solved=0,
                played=0,
                available=released,
                win_rate=None,
                average_completion_time_seconds=None,
            )
    released_total = sum(catalog.get(puzzle_type, 0) for puzzle_type in _CATEGORY_TYPES)
    opened = sum(min(buckets[puzzle_type].played, buckets[puzzle_type].available) for puzzle_type in _CATEGORY_TYPES)
    return StatsSlice(
        puzzles_solved=solved,
        puzzles_played=played,
        puzzles_available=released_total,
        completion_percent=None
        if released_total == 0
        else round(100.0 * solved / released_total, 1),
        left_to_play=max(0, released_total - opened),
        win_rate=_percent(solved, played),
        average_completion_time_seconds=_average(time_sum, solved),
        categories=CategoryBreakdown(
            pattern=buckets[PuzzleType.PATTERN],
            anagram=buckets[PuzzleType.ANAGRAM],
            news_quiz=buckets[PuzzleType.NEWS_QUIZ],
        ),
    )


def _add(
    totals: dict[PuzzleType, tuple[int, int, int]],
    puzzle_type: PuzzleType,
    played: int,
    solved: int,
    time_sum: int,
) -> None:
    current = totals.get(puzzle_type, (0, 0, 0))
    totals[puzzle_type] = (
        current[0] + played,
        current[1] + solved,
        current[2] + time_sum,
    )


async def user_stats(session: AsyncSession, user: User, today: date) -> UserStatsRead:
    correct = UserCompletion.is_correct.is_(True)
    played_on_assigned_day = func.date(
        func.timezone("UTC", UserCompletion.completed_at)
    ) == Puzzle.assigned_date
    is_daily = or_(UserCompletion.is_daily_official.is_(True), played_on_assigned_day)
    rows = (
        await session.execute(
            select(
                Puzzle.puzzle_type,
                is_daily.label("is_daily"),
                func.count().label("played"),
                func.count().filter(correct).label("solved"),
                func.coalesce(
                    func.sum(UserCompletion.time_taken_seconds).filter(correct),
                    0,
                ).label("time_sum"),
            )
            .join(Puzzle, Puzzle.id == UserCompletion.puzzle_id)
            .where(UserCompletion.user_id == user.id)
            .group_by(Puzzle.puzzle_type, is_daily)
        )
    ).all()

    daily: dict[PuzzleType, tuple[int, int, int]] = {}
    overall: dict[PuzzleType, tuple[int, int, int]] = {}
    for row in rows:
        puzzle_type = row.puzzle_type
        if not isinstance(puzzle_type, PuzzleType):
            puzzle_type = PuzzleType(puzzle_type)
        row_played = int(row.played or 0)
        row_solved = int(row.solved or 0)
        row_time = int(row.time_sum or 0)
        _add(overall, puzzle_type, row_played, row_solved, row_time)
        if row.is_daily:
            _add(daily, puzzle_type, row_played, row_solved, row_time)

    released_rows = (
        await session.execute(
            select(Puzzle.puzzle_type, func.count())
            .where(Puzzle.assigned_date.is_not(None), Puzzle.assigned_date <= today)
            .group_by(Puzzle.puzzle_type)
        )
    ).all()
    released: dict[PuzzleType, int] = {}
    for puzzle_type, count in released_rows:
        if not isinstance(puzzle_type, PuzzleType):
            puzzle_type = PuzzleType(puzzle_type)
        released[puzzle_type] = int(count or 0)

    return UserStatsRead(
        current_streak=display_streak(user.streak_count, user.streak_date, today),
        best_streak=user.best_streak,
        daily=_slice(daily),
        overall=_slice(overall, released),
    )
