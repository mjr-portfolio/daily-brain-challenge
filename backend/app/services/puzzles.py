from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.puzzle import Puzzle, PuzzleType
from app.models.puzzle_start import PuzzleStart
from app.models.user import User
from app.models.user_completion import UserCompletion
from app.schemas.puzzle import (
    AnagramArchiveItem,
    AnagramContent,
    AnagramPuzzleRead,
    ArchivePage,
    ArchivePuzzleItem,
    NewsQuizArchiveItem,
    NewsQuizContent,
    NewsQuizPuzzleRead,
    PatternArchiveItem,
    PatternContent,
    PatternPuzzleRead,
)


async def get_daily_puzzle(session: AsyncSession, today_utc: date) -> Puzzle | None:
    return await session.scalar(
        select(Puzzle).where(Puzzle.assigned_date == today_utc)
    )


async def get_puzzle_by_id(session: AsyncSession, puzzle_id: UUID) -> Puzzle | None:
    return await session.scalar(select(Puzzle).where(Puzzle.id == puzzle_id))


async def get_user_completion(
    session: AsyncSession,
    user_id: UUID,
    puzzle_id: UUID,
) -> UserCompletion | None:
    return await session.scalar(
        select(UserCompletion).where(
            UserCompletion.user_id == user_id,
            UserCompletion.puzzle_id == puzzle_id,
        )
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


def to_archive_item(
    puzzle: Puzzle,
    completion: UserCompletion | None,
) -> ArchivePuzzleItem:
    public = to_puzzle_read(puzzle)
    payload = public.model_dump()
    payload["is_completed"] = completion is not None
    payload["is_correct"] = completion.is_correct if completion is not None else None
    payload["score"] = completion.score if completion is not None else None
    if puzzle.puzzle_type == PuzzleType.PATTERN:
        return PatternArchiveItem.model_validate(payload)
    if puzzle.puzzle_type == PuzzleType.ANAGRAM:
        return AnagramArchiveItem.model_validate(payload)
    if puzzle.puzzle_type == PuzzleType.NEWS_QUIZ:
        return NewsQuizArchiveItem.model_validate(payload)
    raise ValueError(f"Unsupported puzzle_type: {puzzle.puzzle_type}")


async def list_archive_puzzles(
    session: AsyncSession,
    today_utc: date,
    *,
    page: int,
    limit: int,
    puzzle_type: PuzzleType | None,
    user_id: UUID | None,
) -> ArchivePage:
    filters = [
        Puzzle.assigned_date.is_not(None),
        Puzzle.assigned_date < today_utc,
    ]
    if puzzle_type is not None:
        filters.append(Puzzle.puzzle_type == puzzle_type)

    total = int(
        await session.scalar(select(func.count()).select_from(Puzzle).where(*filters)) or 0
    )
    offset = (page - 1) * limit
    order = (Puzzle.assigned_date.desc(), Puzzle.id.desc())

    if user_id is None:
        puzzles = (
            await session.scalars(
                select(Puzzle).where(*filters).order_by(*order).offset(offset).limit(limit)
            )
        ).all()
        rows = [(puzzle, None) for puzzle in puzzles]
    else:
        result = await session.execute(
            select(Puzzle, UserCompletion)
            .outerjoin(
                UserCompletion,
                and_(
                    UserCompletion.puzzle_id == Puzzle.id,
                    UserCompletion.user_id == user_id,
                ),
            )
            .where(*filters)
            .order_by(*order)
            .offset(offset)
            .limit(limit)
        )
        rows = list(result.all())

    return ArchivePage(
        items=[to_archive_item(puzzle, completion) for puzzle, completion in rows],
        page=page,
        limit=limit,
        total=total,
    )


async def get_puzzle_start(
    session: AsyncSession,
    user_id: UUID,
    puzzle_id: UUID,
) -> PuzzleStart | None:
    return await session.scalar(
        select(PuzzleStart).where(
            PuzzleStart.user_id == user_id,
            PuzzleStart.puzzle_id == puzzle_id,
        )
    )


async def begin_puzzle(
    session: AsyncSession,
    puzzle: Puzzle,
    user: User | None,
) -> datetime | None:
    """Record the first signed-in start. A later call returns the original time."""
    if user is None:
        return None
    existing = await get_puzzle_start(session, user.id, puzzle.id)
    if existing is not None:
        return existing.started_at
    started_at = datetime.now(UTC)
    session.add(
        PuzzleStart(
            user_id=user.id,
            puzzle_id=puzzle.id,
            started_at=started_at,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_puzzle_start(session, user.id, puzzle.id)
        if existing is None:
            raise
        return existing.started_at
    return started_at
