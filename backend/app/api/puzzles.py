from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.schemas.puzzle import PuzzleRead
from app.schemas.user_completion import CompletionCreate, SubmitResult
from app.services.puzzles import (
    get_daily_puzzle,
    get_next_archive_puzzle,
    get_puzzle_by_id,
    to_puzzle_read,
)
from app.services.verification import verify_and_record_submission

router = APIRouter(prefix="/puzzles", tags=["puzzles"])


def _today_utc():
    return datetime.now(UTC).date()


@router.get("/daily", response_model=PuzzleRead)
async def get_daily(db: DbSession):
    puzzle = await get_daily_puzzle(db, _today_utc())
    if puzzle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No daily puzzle assigned for today",
        )
    return to_puzzle_read(puzzle)


@router.post("/{puzzle_id}/submit", response_model=SubmitResult)
async def submit_puzzle(
    puzzle_id: UUID,
    payload: CompletionCreate,
    db: DbSession,
    current_user: OptionalUser,
) -> SubmitResult:
    puzzle = await get_puzzle_by_id(db, puzzle_id)
    if puzzle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puzzle not found",
        )

    return await verify_and_record_submission(
        db,
        puzzle,
        payload.answer,
        payload.time_taken_seconds,
        current_user,
        _today_utc(),
    )


@router.get("/archive/next", response_model=PuzzleRead)
async def get_archive_next(db: DbSession, current_user: CurrentUser):
    puzzle = await get_next_archive_puzzle(db, current_user.id, _today_utc())
    if puzzle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No uncompleted archive puzzles available",
        )
    return to_puzzle_read(puzzle)
