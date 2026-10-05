"""Seed sample Pattern Recognition puzzles (daily + archive).

Run from backend/: python -m scripts.seed_puzzles
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

# Allow running as `python scripts/seed_puzzles.py` from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.puzzle import Puzzle, PuzzleType  # noqa: E402
from app.services.hashing import hash_solution  # noqa: E402

SAMPLE_PUZZLES: list[dict] = [
    {
        "offset_days": 0,
        "content": {
            "grid": [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, None],
            ],
            "prompt": "Which number completes the sequence?",
            "choices": [9, 10, 12],
        },
        "solution": 9,
        "explanation": "Each row increases by 1, so the blank is 9.",
    },
    {
        "offset_days": -1,
        "content": {
            "grid": [
                ["A", "B", "C"],
                ["D", "E", "F"],
                ["G", "H", None],
            ],
            "prompt": "Which letter completes the pattern?",
            "choices": ["I", "J", "K"],
        },
        "solution": "I",
        "explanation": "Letters run A through I, so the blank is I.",
    },
    {
        "offset_days": -2,
        "content": {
            "grid": [
                [2, 4, 8],
                [3, 6, 12],
                [4, 8, None],
            ],
            "prompt": "Find the missing value in the pattern.",
            "choices": [16, 14, 10],
        },
        "solution": 16,
        "explanation": "Each row doubles, so the blank is 16.",
    },
]


async def seed() -> None:
    today = date.today()
    created = 0
    updated = 0

    async with AsyncSessionLocal() as session:
        for sample in SAMPLE_PUZZLES:
            assigned = today + timedelta(days=sample["offset_days"])
            existing = await session.scalar(
                select(Puzzle).where(Puzzle.assigned_date == assigned)
            )
            solution_hash = hash_solution(sample["solution"])
            if existing is not None:
                existing.solution = sample["solution"]
                existing.explanation = sample["explanation"]
                existing.solution_hash = solution_hash
                updated += 1
                continue

            session.add(
                Puzzle(
                    puzzle_type=PuzzleType.PATTERN,
                    assigned_date=assigned,
                    content=sample["content"],
                    solution_hash=solution_hash,
                    solution=sample["solution"],
                    explanation=sample["explanation"],
                )
            )
            created += 1

        await session.commit()

    print(f"Seed complete: created={created}, updated={updated}")


if __name__ == "__main__":
    asyncio.run(seed())
