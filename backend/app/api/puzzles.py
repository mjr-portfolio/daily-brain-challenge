from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.models.user_completion import UserCompletion
from app.schemas.puzzle import PuzzleRead
from app.schemas.user_completion import CompletionCreate, SubmitResult
from app.services.percentile import compute_official_percentile
from app.services.puzzles import (
    get_daily_puzzle,
    get_next_archive_puzzle,
    get_puzzle_by_id,
    to_puzzle_read,
)
from app.services.verification import compute_score, is_daily_official, verify_answer

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

    is_correct = verify_answer(puzzle, payload.answer)

    if current_user is None:
        return SubmitResult(
            is_correct=is_correct,
            time_taken_seconds=payload.time_taken_seconds,
            percentile=None,
            score=None,
            is_daily_official=None,
        )

    today = _today_utc()
    official = is_daily_official(puzzle, today)
    score = compute_score(is_correct)

    completion = UserCompletion(
        user_id=current_user.id,
        puzzle_id=puzzle.id,
        is_correct=is_correct,
        score=score,
        time_taken_seconds=payload.time_taken_seconds,
        is_daily_official=official,
    )
    db.add(completion)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Puzzle already completed by this user",
        ) from exc

    percentile = None
    if official and is_correct:
        percentile = await compute_official_percentile(
            db,
            puzzle_id=puzzle.id,
            time_taken_seconds=payload.time_taken_seconds,
        )

    return SubmitResult(
        is_correct=is_correct,
        time_taken_seconds=payload.time_taken_seconds,
        percentile=percentile,
        score=score,
        is_daily_official=official,
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
