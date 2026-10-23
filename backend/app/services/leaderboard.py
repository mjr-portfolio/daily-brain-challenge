"""Ranked official finishes for today's puzzle. Names never include an email."""

from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_completion import UserCompletion
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardRead
from app.services.puzzles import get_daily_puzzle


def anonymous_name(user_id: UUID) -> str:
    number = (user_id.int % 9000) + 1000
    return f"Player #{number}"


def label_users(user_ids: list[UUID]) -> dict[UUID, str]:
    """Stable Player # labels. Collisions inside this set get a short suffix."""
    groups: dict[str, list[UUID]] = {}
    for user_id in user_ids:
        groups.setdefault(anonymous_name(user_id), []).append(user_id)

    labels: dict[UUID, str] = {}
    for base, members in groups.items():
        if len(members) == 1:
            labels[members[0]] = base
            continue
        for user_id in members:
            labels[user_id] = f"{base}-{user_id.hex[-4:]}"
    return labels


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
                UserCompletion.score,
                UserCompletion.time_taken_seconds,
            )
            .where(
                UserCompletion.puzzle_id == puzzle.id,
                UserCompletion.is_daily_official.is_(True),
                UserCompletion.user_id.is_not(None),
            )
            .order_by(
                UserCompletion.score.desc(),
                UserCompletion.time_taken_seconds.asc(),
                UserCompletion.completed_at.asc(),
                UserCompletion.user_id.asc(),
            )
        )
    ).all()

    ranked: list[tuple[int, UUID, int, int]] = []
    for index, row in enumerate(rows, start=1):
        if row.user_id is None:
            continue
        ranked.append((index, row.user_id, int(row.score), int(row.time_taken_seconds)))

    page = ranked[:limit]
    viewer_row = next((row for row in ranked if row[1] == viewer_id), None)
    shown_ids = [row[1] for row in page]
    if viewer_row is not None and viewer_row[1] not in shown_ids:
        shown_ids.append(viewer_row[1])
    labels = label_users(shown_ids)

    def entry(row: tuple[int, UUID, int, int], *, is_viewer: bool) -> LeaderboardEntry:
        rank, user_id, score, seconds = row
        return LeaderboardEntry(
            rank=rank,
            display_name=labels[user_id],
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
