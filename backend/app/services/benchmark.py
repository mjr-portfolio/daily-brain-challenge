"""Live-day snapshot for an archived puzzle. Official rows only; this read never writes."""

from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_completion import UserCompletion
from app.schemas.leaderboard import ArchiveBenchmark, BenchmarkViewer
from app.services.percentile import compute_official_percentile
from app.services.puzzles import get_puzzle_by_id, get_user_completion


def _official_correct(puzzle_id: UUID):
    return (
        UserCompletion.puzzle_id == puzzle_id,
        UserCompletion.is_daily_official.is_(True),
        UserCompletion.is_correct.is_(True),
    )


async def _faster_than_percent(
    session: AsyncSession,
    *,
    puzzle_id: UUID,
    time_taken_seconds: int,
    viewer_in_pool: bool,
) -> float | None:
    if viewer_in_pool:
        percent = await compute_official_percentile(
            session,
            puzzle_id=puzzle_id,
            time_taken_seconds=time_taken_seconds,
        )
        if percent is None:
            return None
        return round(percent, 1)

    filters = _official_correct(puzzle_id)
    total = await session.scalar(
        select(func.count()).select_from(UserCompletion).where(*filters)
    )
    if not total:
        return None
    slower = await session.scalar(
        select(func.count())
        .select_from(UserCompletion)
        .where(*filters, UserCompletion.time_taken_seconds > time_taken_seconds)
    )
    return round(100.0 * float(slower or 0) / float(total), 1)


async def archive_benchmark(
    session: AsyncSession,
    puzzle_id: UUID,
    *,
    viewer_id: UUID,
    today: date,
) -> ArchiveBenchmark:
    puzzle = await get_puzzle_by_id(session, puzzle_id)
    if puzzle is None or puzzle.assigned_date is None or puzzle.assigned_date >= today:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archived puzzle not found",
        )

    filters = _official_correct(puzzle.id)
    summary = (
        await session.execute(
            select(
                func.count().label("solver_count"),
                func.min(UserCompletion.time_taken_seconds).label("fastest_time"),
                func.percentile_cont(0.5)
                .within_group(UserCompletion.time_taken_seconds)
                .label("median_time"),
                func.avg(UserCompletion.score).label("average_score"),
            ).where(*filters)
        )
    ).one()

    solver_count = int(summary.solver_count or 0)
    fastest = None if summary.fastest_time is None else int(summary.fastest_time)
    median = None if summary.median_time is None else round(float(summary.median_time), 1)
    average = None if summary.average_score is None else round(float(summary.average_score), 1)

    completion = await get_user_completion(session, viewer_id, puzzle.id)
    viewer = None
    if completion is not None:
        percent = None
        if completion.is_correct and solver_count > 0:
            percent = await _faster_than_percent(
                session,
                puzzle_id=puzzle.id,
                time_taken_seconds=completion.time_taken_seconds,
                viewer_in_pool=completion.is_daily_official,
            )
        viewer = BenchmarkViewer(
            time_taken_seconds=completion.time_taken_seconds,
            score=completion.score,
            is_correct=completion.is_correct,
            faster_than_percent=percent,
        )

    return ArchiveBenchmark(
        puzzle_id=puzzle.id,
        assigned_date=puzzle.assigned_date,
        solver_count=solver_count,
        fastest_completion_time_seconds=fastest,
        median_completion_time_seconds=median,
        average_score=average,
        viewer=viewer,
    )
