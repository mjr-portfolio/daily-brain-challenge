from datetime import UTC, date, datetime
from typing import cast

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.puzzle import Puzzle, PuzzleType
from app.models.user import User
from app.models.user_completion import UserCompletion
from app.schemas.puzzle import ShapeItem
from app.schemas.user_completion import AnswerType, SubmitResult
from app.services.hashing import hash_solution
from app.services.percentile import compute_official_percentile
from app.services.puzzles import get_puzzle_start
from app.services.streak import apply_daily_result, display_streak


_TEXT_PUZZLE_TYPES = {PuzzleType.ANAGRAM, PuzzleType.NEWS_QUIZ}


def _is_text_puzzle(puzzle: object) -> bool:
    return getattr(puzzle, "puzzle_type", None) in _TEXT_PUZZLE_TYPES


def verify_answer(puzzle: Puzzle, answer: object) -> bool:
    if _is_text_puzzle(puzzle):
        return _verify_text_answer(puzzle, answer)
    return _hash_pattern_answer(answer) == puzzle.solution_hash


def _hash_pattern_answer(answer: object) -> str:
    if isinstance(answer, ShapeItem):
        return hash_solution(answer.model_dump())
    if isinstance(answer, dict):
        try:
            return hash_solution(ShapeItem.model_validate(answer).model_dump())
        except ValidationError:
            return hash_solution(answer)
    return hash_solution(answer)


def _verify_text_answer(puzzle: Puzzle, answer: object) -> bool:
    if not isinstance(answer, str):
        return False
    solution = puzzle.solution
    if not isinstance(solution, str):
        return False
    return answer.strip().casefold() == solution.strip().casefold()


def compute_score(is_correct: bool, time_taken_seconds: int) -> int:
    """100 for a correct answer within 10 seconds, then -1 per extra second, floored at 1."""
    if not is_correct:
        return 0
    penalty = max(0, time_taken_seconds - 10)
    return max(1, 100 - penalty)


def is_daily_official(puzzle: Puzzle, today_utc: date) -> bool:
    return puzzle.assigned_date == today_utc


def elapsed_seconds(started_at: datetime, now: datetime) -> int:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    return max(0, int((now - started_at).total_seconds()))


def _require_reveal(puzzle: Puzzle) -> tuple[AnswerType, str]:
    answer = puzzle.solution
    explanation = puzzle.explanation
    if (
        explanation is None
        or not _is_answer(answer)
        or (_is_text_puzzle(puzzle) and not isinstance(answer, str))
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Puzzle solution is unavailable",
        )
    return cast(AnswerType, answer), explanation


def _is_shape_answer(value: object) -> bool:
    if isinstance(value, ShapeItem):
        return True
    if not isinstance(value, dict):
        return False
    try:
        ShapeItem.model_validate(value)
    except ValidationError:
        return False
    return True


def _is_answer(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | str) or _is_shape_answer(value):
        return True
    if isinstance(value, list):
        return all(_is_answer(item) and not isinstance(item, list) for item in value)
    return False


async def verify_and_record_submission(
    session: AsyncSession,
    puzzle: Puzzle,
    answer: AnswerType,
    time_taken_seconds: int,
    user: User | None,
    today_utc: date,
) -> SubmitResult:
    if user is None and not is_daily_official(puzzle, today_utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to play archive puzzles",
            headers={"WWW-Authenticate": "Bearer"},
        )

    correct_answer, explanation = _require_reveal(puzzle)
    is_correct = verify_answer(puzzle, answer)

    if user is None:
        return SubmitResult(
            is_correct=is_correct,
            time_taken_seconds=time_taken_seconds,
            correct_answer=correct_answer,
            explanation=explanation,
            percentile=None,
            score=None,
            is_daily_official=None,
        )

    ranked = False
    played_today = is_daily_official(puzzle, today_utc)
    if played_today:
        start = await get_puzzle_start(session, user.id, puzzle.id)
        if start is not None:
            time_taken_seconds = elapsed_seconds(start.started_at, datetime.now(UTC))
            ranked = True
        user.streak_count, user.streak_date = apply_daily_result(
            user.streak_count,
            user.streak_date,
            today_utc,
        )
    elif user.streak_date is not None and display_streak(
        user.streak_count, user.streak_date, today_utc
    ) == 0:
        user.streak_count = 0
    score = compute_score(is_correct, time_taken_seconds)
    session.add(
        UserCompletion(
            user_id=user.id,
            puzzle_id=puzzle.id,
            is_correct=is_correct,
            score=score,
            time_taken_seconds=time_taken_seconds,
            is_daily_official=ranked,
        )
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Puzzle already completed by this user",
        ) from exc

    percentile = None
    if ranked and is_correct:
        percentile = await compute_official_percentile(
            session,
            puzzle_id=puzzle.id,
            time_taken_seconds=time_taken_seconds,
        )

    return SubmitResult(
        is_correct=is_correct,
        time_taken_seconds=time_taken_seconds,
        correct_answer=correct_answer,
        explanation=explanation,
        percentile=percentile,
        score=score,
        is_daily_official=ranked,
        streak=display_streak(user.streak_count, user.streak_date, today_utc),
    )
