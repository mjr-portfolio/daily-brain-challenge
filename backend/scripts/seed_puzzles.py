"""Seed sample Pattern Recognition puzzles (daily + archive).

Run from backend/: python -m scripts.seed_puzzles
"""

from __future__ import annotations

import asyncio
import hashlib
import json
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


def hash_solution(solution: object) -> str:
    payload = json.dumps(solution, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    },
]


async def seed() -> None:
    today = date.today()
    created = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        for sample in SAMPLE_PUZZLES:
            assigned = today + timedelta(days=sample["offset_days"])
            existing = await session.scalar(
                select(Puzzle).where(Puzzle.assigned_date == assigned)
            )
            if existing is not None:
                skipped += 1
                continue

            session.add(
                Puzzle(
                    puzzle_type=PuzzleType.PATTERN,
                    assigned_date=assigned,
                    content=sample["content"],
                    solution_hash=hash_solution(sample["solution"]),
                )
            )
            created += 1

        await session.commit()

    print(f"Seed complete: created={created}, skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(seed())
