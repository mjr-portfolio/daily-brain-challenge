"""Insert one mock Anagram puzzle for archive UI testing.

Run from backend/: python -m scripts.seed_anagram

Prefers yesterday (UTC). If that date is already assigned, or if it is one of the
past dates the archive tests insert, picks the nearest earlier free date so the
row does not collide and is the oldest archive puzzle.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

# Allow running as `python scripts/seed_anagram.py` from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.puzzle import Puzzle, PuzzleType  # noqa: E402
from app.services.hashing import hash_solution  # noqa: E402

TARGET_WORD = "REACT"
EXPLANATION = "REACT is an anagram of EACRT."
CONTENT = {
    "scrambled_word": "EACRT",
    "prompt": "Unscramble the letters to reveal the target word",
    "hint": "A modern web UI library",
}
# Offsets used by tests/test_puzzles_archive.py relative to UTC today.
ARCHIVE_TEST_OFFSETS = {3, 5, 90}


def _reserved_dates(today):
    return {today - timedelta(days=offset) for offset in ARCHIVE_TEST_OFFSETS}


async def _assigned_dates(session) -> set:
    rows = await session.scalars(select(Puzzle.assigned_date))
    return {assigned for assigned in rows if assigned is not None}


def choose_assigned_date(today, taken: set):
    """Yesterday when free; otherwise a free date older than the current archive."""
    blocked = taken | _reserved_dates(today) | {today}
    yesterday = today - timedelta(days=1)
    older_than_yesterday = [assigned for assigned in taken if assigned < yesterday]
    if yesterday not in blocked and not older_than_yesterday:
        return yesterday, False

    oldest = min(older_than_yesterday, default=yesterday)
    candidate = min(oldest, yesterday) - timedelta(days=1)
    while candidate in blocked:
        candidate -= timedelta(days=1)
    return candidate, True


async def seed() -> None:
    today = datetime.now(UTC).date()

    async with AsyncSessionLocal() as session:
        existing = (
            await session.scalars(select(Puzzle).where(Puzzle.puzzle_type == PuzzleType.ANAGRAM))
        ).all()
        for puzzle in existing:
            if puzzle.content.get("scrambled_word") == CONTENT["scrambled_word"]:
                print(
                    "Anagram already seeded: "
                    f"id={puzzle.id} assigned_date={puzzle.assigned_date}"
                )
                return

        taken = await _assigned_dates(session)
        assigned, shifted = choose_assigned_date(today, taken)
        if shifted:
            print(
                f"Yesterday {today - timedelta(days=1)} is already assigned; "
                f"using {assigned} so the anagram is the next archive puzzle."
            )

        puzzle = Puzzle(
            puzzle_type=PuzzleType.ANAGRAM,
            assigned_date=assigned,
            content=CONTENT,
            solution_hash=hash_solution(TARGET_WORD),
            solution=TARGET_WORD,
            explanation=EXPLANATION,
        )
        session.add(puzzle)
        await session.commit()
        await session.refresh(puzzle)

    print(f"Seeded anagram: id={puzzle.id} assigned_date={puzzle.assigned_date} solution={TARGET_WORD}")


if __name__ == "__main__":
    asyncio.run(seed())
