"""Puzzle queue schedule, reserve inventory, and replenishment."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.puzzle import Puzzle, PuzzleType
from app.services.generator import GenerationError, GeneratedPuzzle, generate_puzzle

logger = logging.getLogger(__name__)

ROTATION: tuple[PuzzleType, ...] = (
    PuzzleType.PATTERN,
    PuzzleType.ANAGRAM,
    PuzzleType.NEWS_QUIZ,
)
FIXED_WEEKDAY_ENGINES: dict[int, PuzzleType] = {
    0: PuzzleType.PATTERN,  # Monday
    2: PuzzleType.ANAGRAM,  # Wednesday
    4: PuzzleType.NEWS_QUIZ,  # Friday
}
RESERVE_TARGET_PER_TYPE = 2


def engine_for_date(d: date) -> PuzzleType:
    weekday = d.weekday()
    fixed = FIXED_WEEKDAY_ENGINES.get(weekday)
    if fixed is not None:
        return fixed
    iso_week = d.isocalendar().week
    return ROTATION[(iso_week + weekday) % len(ROTATION)]


async def missing_horizon_dates(
    session: AsyncSession,
    today: date,
    target_days: int,
) -> list[date]:
    horizon = [today + timedelta(days=offset) for offset in range(target_days)]
    existing = set(
        await session.scalars(
            select(Puzzle.assigned_date).where(Puzzle.assigned_date.in_(horizon))
        )
    )
    return [day for day in horizon if day not in existing]


async def reserve_counts(session: AsyncSession) -> dict[PuzzleType, int]:
    rows = await session.execute(
        select(Puzzle.puzzle_type, func.count())
        .where(Puzzle.assigned_date.is_(None))
        .group_by(Puzzle.puzzle_type)
    )
    counts = {puzzle_type: 0 for puzzle_type in PuzzleType}
    for puzzle_type, count in rows.all():
        counts[puzzle_type] = int(count)
    return counts


async def claim_reserve(
    session: AsyncSession,
    puzzle_type: PuzzleType,
    assigned_date: date,
) -> Puzzle | None:
    puzzle = await session.scalar(
        select(Puzzle)
        .where(
            Puzzle.assigned_date.is_(None),
            Puzzle.puzzle_type == puzzle_type,
        )
        .order_by(Puzzle.created_at.asc())
        .limit(1)
    )
    if puzzle is None:
        return None
    puzzle.assigned_date = assigned_date
    await session.commit()
    await session.refresh(puzzle)
    return puzzle


def _puzzle_from_generated(
    generated: GeneratedPuzzle,
    *,
    assigned_date: date | None,
) -> Puzzle:
    return Puzzle(
        puzzle_type=generated.puzzle_type,
        assigned_date=assigned_date,
        content=generated.content,
        solution_hash=generated.solution_hash,
        solution=generated.solution,
        explanation=generated.explanation,
    )


async def _generate_in_thread(puzzle_type: PuzzleType) -> GeneratedPuzzle:
    return await asyncio.to_thread(generate_puzzle, puzzle_type)


async def replenish_queue(
    session: AsyncSession,
    *,
    today: date | None = None,
    target_days: int = 7,
) -> dict[str, Any]:
    if today is None:
        today = datetime.now(UTC).date()
    if target_days < 1:
        raise ValueError("target_days must be >= 1")

    summary: dict[str, Any] = {
        "created_assigned": 0,
        "promoted_reserve": 0,
        "created_reserve": 0,
        "failures": [],
    }
    # Free-tier Gemini limit is 5 RPM; pace consecutive generate_* calls.
    paced_generate = False

    missing = await missing_horizon_dates(session, today, target_days)
    for day in missing:
        desired = engine_for_date(day)
        if paced_generate:
            await asyncio.sleep(13)
        try:
            generated = await _generate_in_thread(desired)
            paced_generate = True
            session.add(_puzzle_from_generated(generated, assigned_date=day))
            await session.commit()
            summary["created_assigned"] += 1
            continue
        except Exception as exc:
            paced_generate = True
            await session.rollback()
            logger.warning("Generation failed for %s on %s: %s", desired.value, day, exc)

        promoted = await claim_reserve(session, desired, day)
        if promoted is not None:
            summary["promoted_reserve"] += 1
            logger.info(
                "Promoted reserve puzzle %s (%s) to %s",
                promoted.id,
                desired.value,
                day,
            )
            continue

        summary["failures"].append(
            {"phase": "horizon", "date": day.isoformat(), "puzzle_type": desired.value}
        )
        logger.error("Unable to fill horizon date %s for type %s", day, desired.value)

    counts = await reserve_counts(session)
    for puzzle_type in ROTATION:
        needed = RESERVE_TARGET_PER_TYPE - counts.get(puzzle_type, 0)
        for _ in range(max(0, needed)):
            if paced_generate:
                await asyncio.sleep(13)
            try:
                generated = await _generate_in_thread(puzzle_type)
                paced_generate = True
                session.add(_puzzle_from_generated(generated, assigned_date=None))
                await session.commit()
                summary["created_reserve"] += 1
            except Exception as exc:
                paced_generate = True
                await session.rollback()
                summary["failures"].append(
                    {
                        "phase": "reserve",
                        "puzzle_type": puzzle_type.value,
                        "error": str(exc),
                    }
                )
                logger.warning(
                    "Reserve generation failed for %s: %s",
                    puzzle_type.value,
                    exc,
                )
                if isinstance(exc, GenerationError):
                    break

    return summary
