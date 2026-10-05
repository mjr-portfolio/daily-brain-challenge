from datetime import date
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.puzzle import Puzzle, PuzzleType
from app.models.user_completion import UserCompletion
from app.schemas.puzzle import (
    AnagramContent,
    AnagramPuzzleRead,
    NewsQuizContent,
    NewsQuizPuzzleRead,
    PatternContent,
    PatternPuzzleRead,
)


async def get_daily_puzzle(session: AsyncSession, today_utc: date) -> Puzzle | None:
    return await session.scalar(
        select(Puzzle).where(Puzzle.assigned_date == today_utc)
    )


async def get_puzzle_by_id(session: AsyncSession, puzzle_id: UUID) -> Puzzle | None:
    return await session.scalar(select(Puzzle).where(Puzzle.id == puzzle_id))


async def get_next_archive_puzzle(
    session: AsyncSession,
    user_id: UUID,
    today_utc: date,
) -> Puzzle | None:
    completion_exists = exists(
        select(UserCompletion.id).where(
            UserCompletion.puzzle_id == Puzzle.id,
            UserCompletion.user_id == user_id,
        )
    )
    return await session.scalar(
        select(Puzzle)
        .where(
            Puzzle.assigned_date.is_not(None),
            Puzzle.assigned_date < today_utc,
            ~completion_exists,
        )
        .order_by(Puzzle.assigned_date.asc())
        .limit(1)
    )


def to_puzzle_read(
    puzzle: Puzzle,
) -> PatternPuzzleRead | AnagramPuzzleRead | NewsQuizPuzzleRead:
    """Map ORM puzzle to public read schema (never includes solution_hash)."""
    if puzzle.puzzle_type == PuzzleType.PATTERN:
        return PatternPuzzleRead(
            id=puzzle.id,
            puzzle_type=PuzzleType.PATTERN,
            assigned_date=puzzle.assigned_date,
            created_at=puzzle.created_at,
            content=PatternContent.model_validate(puzzle.content),
        )
    if puzzle.puzzle_type == PuzzleType.ANAGRAM:
        return AnagramPuzzleRead(
            id=puzzle.id,
            puzzle_type=PuzzleType.ANAGRAM,
            assigned_date=puzzle.assigned_date,
            created_at=puzzle.created_at,
            content=AnagramContent.model_validate(puzzle.content),
        )
    if puzzle.puzzle_type == PuzzleType.NEWS_QUIZ:
        return NewsQuizPuzzleRead(
            id=puzzle.id,
            puzzle_type=PuzzleType.NEWS_QUIZ,
            assigned_date=puzzle.assigned_date,
            created_at=puzzle.created_at,
            content=NewsQuizContent.model_validate(puzzle.content),
        )
    raise ValueError(f"Unsupported puzzle_type: {puzzle.puzzle_type}")
