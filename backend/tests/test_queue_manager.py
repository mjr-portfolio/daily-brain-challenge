from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.puzzle import Puzzle, PuzzleType
from app.services.generator import GeneratedPuzzle, GenerationError
from app.services.hashing import hash_solution
from app.services.queue_manager import (
    claim_reserve,
    engine_for_date,
    missing_horizon_dates,
    replenish_queue,
    reserve_counts,
)
from tests.conftest import cleanup_puzzle, create_puzzle


def test_engine_for_date_fixed_weekdays() -> None:
    # 2026-10-05 is a Monday
    assert engine_for_date(date(2026, 10, 5)) == PuzzleType.PATTERN
    # Wednesday
    assert engine_for_date(date(2026, 10, 7)) == PuzzleType.ANAGRAM
    # Friday
    assert engine_for_date(date(2026, 10, 9)) == PuzzleType.NEWS_QUIZ


def test_engine_for_date_rotating_days_are_deterministic() -> None:
    tuesday = date(2026, 10, 6)
    thursday = date(2026, 10, 8)
    saturday = date(2026, 10, 10)
    sunday = date(2026, 10, 11)

    assert engine_for_date(tuesday) == engine_for_date(tuesday)
    assert engine_for_date(thursday) in {
        PuzzleType.PATTERN,
        PuzzleType.ANAGRAM,
        PuzzleType.NEWS_QUIZ,
    }
    assert engine_for_date(saturday) in {
        PuzzleType.PATTERN,
        PuzzleType.ANAGRAM,
        PuzzleType.NEWS_QUIZ,
    }
    assert engine_for_date(sunday) in {
        PuzzleType.PATTERN,
        PuzzleType.ANAGRAM,
        PuzzleType.NEWS_QUIZ,
    }

    iso_week = tuesday.isocalendar().week
    expected = (
        PuzzleType.PATTERN,
        PuzzleType.ANAGRAM,
        PuzzleType.NEWS_QUIZ,
    )[(iso_week + tuesday.weekday()) % 3]
    assert engine_for_date(tuesday) == expected


@pytest.mark.asyncio
async def test_missing_horizon_and_reserve_counts(session, today_utc) -> None:
    far = today_utc + timedelta(days=40)
    assigned = await create_puzzle(session, assigned=far, solution=9)
    reserve = Puzzle(
        puzzle_type=PuzzleType.ANAGRAM,
        assigned_date=None,
        content={
            "scrambled_word": "EACRT",
            "prompt": "Unscramble",
            "hint": "UI lib",
        },
        solution_hash=hash_solution("REACT"),
        solution="REACT",
        explanation="REACT",
    )
    session.add(reserve)
    await session.commit()
    await session.refresh(reserve)

    missing = await missing_horizon_dates(session, today_utc, target_days=2)
    assert today_utc in missing or today_utc not in missing
    # far date is outside the 2-day window
    assert far not in missing
    assert len(missing) <= 2

    counts = await reserve_counts(session)
    assert counts[PuzzleType.ANAGRAM] >= 1

    await cleanup_puzzle(session, assigned.id)
    await cleanup_puzzle(session, reserve.id)


@pytest.mark.asyncio
async def test_claim_reserve_promotes_oldest(session, today_utc) -> None:
    older = Puzzle(
        puzzle_type=PuzzleType.PATTERN,
        assigned_date=None,
        content={
            "grid": [[1, 2, 3], [4, 5, 6], [7, 8, None]],
            "prompt": "n?",
            "choices": [9, 10, 12],
        },
        solution_hash=hash_solution(9),
        solution=9,
        explanation="nine",
    )
    newer = Puzzle(
        puzzle_type=PuzzleType.PATTERN,
        assigned_date=None,
        content={
            "grid": [[2, 4, 8], [3, 6, 12], [4, 8, None]],
            "prompt": "n?",
            "choices": [16, 14, 10],
        },
        solution_hash=hash_solution(16),
        solution=16,
        explanation="sixteen",
    )
    session.add_all([older, newer])
    await session.commit()
    await session.refresh(older)
    await session.refresh(newer)

    target = today_utc + timedelta(days=50)
    claimed = await claim_reserve(session, PuzzleType.PATTERN, target)
    assert claimed is not None
    assert claimed.id == older.id
    assert claimed.assigned_date == target

    await cleanup_puzzle(session, older.id)
    await cleanup_puzzle(session, newer.id)


def _fake_generated(puzzle_type: PuzzleType, solution: object) -> GeneratedPuzzle:
    if puzzle_type == PuzzleType.PATTERN:
        content = {
            "grid": [[1, 2, 3], [4, 5, 6], [7, 8, None]],
            "prompt": "Which number completes the sequence?",
            "choices": [9, 10, 12],
        }
    elif puzzle_type == PuzzleType.ANAGRAM:
        content = {
            "scrambled_word": "EACRT",
            "prompt": "Unscramble",
            "hint": "UI",
        }
    else:
        content = {
            "question": "Who?",
            "options": ["Meta", "Google", "Microsoft", "Apple"],
            "source_headline": "Briefing",
            "hint": None,
        }
    return GeneratedPuzzle(
        puzzle_type=puzzle_type,
        content=content,
        solution=solution,
        explanation="test",
        solution_hash=hash_solution(solution),
    )


@pytest.mark.asyncio
async def test_replenish_creates_assigned_when_generation_succeeds(
    session, today_utc
) -> None:
    day = today_utc + timedelta(days=55)
    desired = engine_for_date(day)

    solutions = {
        PuzzleType.PATTERN: 9,
        PuzzleType.ANAGRAM: "REACT",
        PuzzleType.NEWS_QUIZ: "Google",
    }

    async def fake_generate(puzzle_type: PuzzleType) -> GeneratedPuzzle:
        return _fake_generated(puzzle_type, solutions[puzzle_type])

    with patch(
        "app.services.queue_manager._generate_in_thread",
        new=AsyncMock(side_effect=fake_generate),
    ):
        with patch(
            "app.services.queue_manager.missing_horizon_dates",
            new=AsyncMock(return_value=[day]),
        ):
            with patch(
                "app.services.queue_manager.reserve_counts",
                new=AsyncMock(
                    return_value={
                        PuzzleType.PATTERN: 2,
                        PuzzleType.ANAGRAM: 2,
                        PuzzleType.NEWS_QUIZ: 2,
                    }
                ),
            ):
                summary = await replenish_queue(
                    session, today=today_utc, target_days=1
                )

    assert summary["created_assigned"] == 1
    assert summary["promoted_reserve"] == 0
    puzzle = await session.scalar(select(Puzzle).where(Puzzle.assigned_date == day))
    assert puzzle is not None
    assert puzzle.puzzle_type == desired
    await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_replenish_promotes_reserve_when_generation_fails(
    session, today_utc
) -> None:
    day = today_utc + timedelta(days=56)
    desired = engine_for_date(day)
    solution = {
        PuzzleType.PATTERN: 9,
        PuzzleType.ANAGRAM: "REACT",
        PuzzleType.NEWS_QUIZ: "Google",
    }[desired]
    reserve = Puzzle(
        puzzle_type=desired,
        assigned_date=None,
        content=_fake_generated(desired, solution).content,
        solution_hash=hash_solution(solution),
        solution=solution,
        explanation="reserve",
    )
    session.add(reserve)
    await session.commit()
    await session.refresh(reserve)

    with patch(
        "app.services.queue_manager._generate_in_thread",
        new=AsyncMock(side_effect=GenerationError("boom")),
    ):
        with patch(
            "app.services.queue_manager.missing_horizon_dates",
            new=AsyncMock(return_value=[day]),
        ):
            with patch(
                "app.services.queue_manager.reserve_counts",
                new=AsyncMock(
                    return_value={
                        PuzzleType.PATTERN: 2,
                        PuzzleType.ANAGRAM: 2,
                        PuzzleType.NEWS_QUIZ: 2,
                    }
                ),
            ):
                summary = await replenish_queue(
                    session, today=today_utc, target_days=1
                )

    assert summary["created_assigned"] == 0
    assert summary["promoted_reserve"] == 1
    await session.refresh(reserve)
    assert reserve.assigned_date == day
    await cleanup_puzzle(session, reserve.id)
