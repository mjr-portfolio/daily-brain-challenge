from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.models.puzzle import PuzzleType
from app.schemas.puzzle import ArchivePage, DailyPreview, DailySession
from app.schemas.user_completion import CompletionCreate, SubmitResult
from app.services.puzzles import (
    begin_puzzle,
    get_daily_puzzle,
    get_puzzle_by_id,
    get_puzzle_start,
    get_user_completion,
    list_archive_puzzles,
    to_puzzle_read,
)
from app.services.verification import verify_and_record_submission

router = APIRouter(prefix="/puzzles", tags=["puzzles"])


def _today_utc():
    return datetime.now(UTC).date()


@router.get("/daily", response_model=DailyPreview)
async def get_daily(db: DbSession, current_user: OptionalUser) -> DailyPreview:
    puzzle = await get_daily_puzzle(db, _today_utc())
    if puzzle is None or puzzle.assigned_date is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No daily puzzle assigned for today",
        )
    is_completed = False
    started_at = None
    if current_user is not None:
        completion = await get_user_completion(db, current_user.id, puzzle.id)
        is_completed = completion is not None
        start = await get_puzzle_start(db, current_user.id, puzzle.id)
        started_at = None if start is None else start.started_at
    return DailyPreview(
        id=puzzle.id,
        puzzle_type=puzzle.puzzle_type,
        assigned_date=puzzle.assigned_date,
        is_completed=is_completed,
        started_at=started_at,
    )


@router.post("/daily/start", response_model=DailySession)
async def start_daily(db: DbSession, current_user: OptionalUser) -> DailySession:
    puzzle = await get_daily_puzzle(db, _today_utc())
    if puzzle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No daily puzzle assigned for today",
        )
    started_at = await begin_puzzle(db, puzzle, current_user)
    public = to_puzzle_read(puzzle)
    if current_user is not None:
        completion = await get_user_completion(db, current_user.id, puzzle.id)
        public = public.model_copy(update={"is_completed": completion is not None})
    return DailySession(
        puzzle=public,
        started_at=started_at,
        server_now=datetime.now(UTC),
    )


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


@router.get("/archive", response_model=ArchivePage)
async def get_archive(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    puzzle_type: PuzzleType | None = None,
) -> ArchivePage:
    return await list_archive_puzzles(
        db,
        _today_utc(),
        page=page,
        limit=limit,
        puzzle_type=puzzle_type,
        user_id=current_user.id,
    )
