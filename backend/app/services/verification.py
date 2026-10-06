from datetime import date
from typing import cast

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.puzzle import Puzzle, PuzzleType
from app.models.user import User
from app.models.user_completion import UserCompletion
from app.schemas.user_completion import AnswerType, SubmitResult
from app.services.hashing import hash_solution
from app.services.percentile import compute_official_percentile


def _is_anagram(puzzle: object) -> bool:
    return getattr(puzzle, "puzzle_type", None) == PuzzleType.ANAGRAM


def verify_answer(puzzle: Puzzle, answer: object) -> bool:
    if _is_anagram(puzzle):
        return _verify_anagram(puzzle, answer)
    return hash_solution(answer) == puzzle.solution_hash


def _verify_anagram(puzzle: Puzzle, answer: object) -> bool:
    if not isinstance(answer, str):
        return False
    solution = puzzle.solution
    if not isinstance(solution, str):
        return False
    return answer.strip().casefold() == solution.strip().casefold()


def compute_score(is_correct: bool) -> int:
    return 100 if is_correct else 0


def is_daily_official(puzzle: Puzzle, today_utc: date) -> bool:
    return puzzle.assigned_date == today_utc


def _require_reveal(puzzle: Puzzle) -> tuple[AnswerType, str]:
    answer = puzzle.solution
    explanation = puzzle.explanation
    if (
        explanation is None
        or not _is_answer(answer)
        or (_is_anagram(puzzle) and not isinstance(answer, str))
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Puzzle solution is unavailable",
        )
    return cast(AnswerType, answer), explanation


def _is_answer(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | str):
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

    official = is_daily_official(puzzle, today_utc)
    score = compute_score(is_correct)
    session.add(
        UserCompletion(
            user_id=user.id,
            puzzle_id=puzzle.id,
            is_correct=is_correct,
            score=score,
            time_taken_seconds=time_taken_seconds,
            is_daily_official=official,
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
    if official and is_correct:
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
        is_daily_official=official,
    )
