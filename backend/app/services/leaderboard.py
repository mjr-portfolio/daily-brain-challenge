"""Ranked official finishes for today's puzzle. Names never include an email."""

from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_completion import UserCompletion
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardRead
from app.services.puzzles import get_daily_puzzle


async def daily_leaderboard(
    session: AsyncSession,
    today: date,
    *,
    viewer_id: UUID | None,
    limit: int,
) -> LeaderboardRead:
    puzzle = await get_daily_puzzle(session, today)
    if puzzle is None or puzzle.assigned_date is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No daily puzzle assigned for today",
        )

    rows = (
        await session.execute(
            select(
                UserCompletion.user_id,
                User.display_name,
                UserCompletion.score,
                UserCompletion.time_taken_seconds,
            )
            .join(User, User.id == UserCompletion.user_id)
            .where(
                UserCompletion.puzzle_id == puzzle.id,
                UserCompletion.is_daily_official.is_(True),
            )
            .order_by(
                UserCompletion.score.desc(),
                UserCompletion.time_taken_seconds.asc(),
                UserCompletion.completed_at.asc(),
                UserCompletion.user_id.asc(),
            )
        )
    ).all()

    ranked: list[tuple[int, UUID, str, int, int]] = []
    for index, row in enumerate(rows, start=1):
        if row.user_id is None:
            continue
        ranked.append(
            (index, row.user_id, row.display_name, int(row.score), int(row.time_taken_seconds))
        )

    page = ranked[:limit]
    viewer_row = next((row for row in ranked if row[1] == viewer_id), None)

    def entry(row: tuple[int, UUID, str, int, int], *, is_viewer: bool) -> LeaderboardEntry:
        rank, _user_id, name, score, seconds = row
        return LeaderboardEntry(
            rank=rank,
            display_name=name,
            score=score,
            completion_time_seconds=seconds,
            is_viewer=is_viewer,
        )

    return LeaderboardRead(
        puzzle_id=puzzle.id,
        assigned_date=puzzle.assigned_date,
        limit=limit,
        entries=[entry(row, is_viewer=row[1] == viewer_id) for row in page],
        viewer=None if viewer_row is None else entry(viewer_row, is_viewer=True),
    )
