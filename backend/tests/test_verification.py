from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.puzzle import PuzzleType
from app.services.hashing import hash_solution
from app.services.percentile import compute_official_percentile
from app.services.verification import (
    _require_reveal,
    compute_score,
    is_daily_official,
    verify_answer,
)
from tests.conftest import cleanup_puzzle, cleanup_user, create_puzzle, create_user


def test_hash_solution_stable() -> None:
    assert hash_solution(9) == hash_solution(9)
    assert hash_solution({"a": 1, "b": 2}) == hash_solution({"b": 2, "a": 1})


def test_verify_answer_correct_and_incorrect() -> None:
    puzzle = SimpleNamespace(solution_hash=hash_solution(9))
    assert verify_answer(puzzle, 9) is True
    assert verify_answer(puzzle, 10) is False


def test_verify_anagram_ignores_case_and_whitespace() -> None:
    puzzle = SimpleNamespace(
        puzzle_type=PuzzleType.ANAGRAM,
        solution="apple",
        solution_hash=hash_solution("not-the-answer"),
    )
    assert verify_answer(puzzle, "  APPLE ") is True
    assert verify_answer(puzzle, "Apple") is True


def test_verify_anagram_rejects_wrong_or_non_string() -> None:
    puzzle = SimpleNamespace(
        puzzle_type=PuzzleType.ANAGRAM,
        solution="apple",
        solution_hash=hash_solution("apple"),
    )
    assert verify_answer(puzzle, "apply") is False
    assert verify_answer(puzzle, 1) is False


def test_anagram_non_string_solution_is_unavailable() -> None:
    puzzle = SimpleNamespace(puzzle_type=PuzzleType.ANAGRAM, solution=9, explanation="n/a")
    with pytest.raises(HTTPException) as exc:
        _require_reveal(puzzle)
    assert exc.value.status_code == 500


def test_compute_score() -> None:
    assert compute_score(True) == 100
    assert compute_score(False) == 0


def test_is_daily_official() -> None:
    today = date(2026, 10, 5)
    assert is_daily_official(SimpleNamespace(assigned_date=today), today) is True
    assert is_daily_official(SimpleNamespace(assigned_date=date(2026, 10, 4)), today) is False
    assert is_daily_official(SimpleNamespace(assigned_date=None), today) is False


@pytest.mark.asyncio
async def test_percentile_single_and_multiple(session, today_utc) -> None:
    from app.models import UserCompletion

    puzzle = await create_puzzle(session, assigned=None, solution=9)
    user_a = await create_user(session)
    user_b = await create_user(session)
    user_c = await create_user(session)

    session.add(
        UserCompletion(
            user_id=user_a.id,
            puzzle_id=puzzle.id,
            is_correct=True,
            score=100,
            time_taken_seconds=10,
            is_daily_official=True,
        )
    )
    await session.commit()

    single = await compute_official_percentile(
        session, puzzle_id=puzzle.id, time_taken_seconds=10
    )
    assert single == 100.0

    session.add_all(
        [
            UserCompletion(
                user_id=user_b.id,
                puzzle_id=puzzle.id,
                is_correct=True,
                score=100,
                time_taken_seconds=20,
                is_daily_official=True,
            ),
            UserCompletion(
                user_id=user_c.id,
                puzzle_id=puzzle.id,
                is_correct=True,
                score=100,
                time_taken_seconds=30,
                is_daily_official=True,
            ),
        ]
    )
    await session.commit()

    # time=10 beats both slower (20, 30) => 100 * 2/3
    mid = await compute_official_percentile(
        session, puzzle_id=puzzle.id, time_taken_seconds=10
    )
    assert mid == pytest.approx(100.0 * 2 / 3)

    await cleanup_puzzle(session, puzzle.id)
    await cleanup_user(session, user_a.id)
    await cleanup_user(session, user_b.id)
    await cleanup_user(session, user_c.id)
