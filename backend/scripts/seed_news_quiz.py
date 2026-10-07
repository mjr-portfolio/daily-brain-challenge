"""UPSERT one News Quiz puzzle on yesterday's date for archive UI testing.

Run from backend/: python -m scripts.seed_news_quiz
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

# Allow running as `python scripts/seed_news_quiz.py` from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.puzzle import Puzzle, PuzzleType  # noqa: E402
from app.services.hashing import hash_solution  # noqa: E402

TARGET_ANSWER = "Google"
EXPLANATION = "Google released its updated Gemini developer framework updates."
CONTENT = {
    "question": "Which technology company announced its new open-source AI model suite this week?",
    "options": ["Meta", "Google", "Microsoft", "Apple"],
    "source_headline": "Major Tech Release Weekly Briefing",
}


async def seed() -> None:
    today = datetime.now(UTC).date()
    assigned = today - timedelta(days=1)
    solution_hash = hash_solution(TARGET_ANSWER)

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Puzzle).where(Puzzle.assigned_date == assigned))
        if existing is not None:
            existing.puzzle_type = PuzzleType.NEWS_QUIZ
            existing.content = CONTENT
            existing.solution = TARGET_ANSWER
            existing.solution_hash = solution_hash
            existing.explanation = EXPLANATION
            await session.commit()
            await session.refresh(existing)
            print(
                f"Updated news quiz: id={existing.id} assigned_date={existing.assigned_date} "
                f"solution={TARGET_ANSWER}"
            )
            return

        puzzle = Puzzle(
            puzzle_type=PuzzleType.NEWS_QUIZ,
            assigned_date=assigned,
            content=CONTENT,
            solution_hash=solution_hash,
            solution=TARGET_ANSWER,
            explanation=EXPLANATION,
        )
        session.add(puzzle)
        await session.commit()
        await session.refresh(puzzle)
        print(
            f"Created news quiz: id={puzzle.id} assigned_date={puzzle.assigned_date} "
            f"solution={TARGET_ANSWER}"
        )


if __name__ == "__main__":
    asyncio.run(seed())
