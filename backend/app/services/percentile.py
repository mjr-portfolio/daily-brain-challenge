from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_completion import UserCompletion


async def compute_official_percentile(
    session: AsyncSession,
    *,
    puzzle_id: UUID,
    time_taken_seconds: int,
) -> float | None:
    """Return percentile 0-100 among official correct completers.

    percentile = 100 * (count with slower time) / total
    When total == 1, return 100.0.
    """
    filters = (
        UserCompletion.puzzle_id == puzzle_id,
        UserCompletion.is_daily_official.is_(True),
        UserCompletion.is_correct.is_(True),
    )

    total = await session.scalar(
        select(func.count()).select_from(UserCompletion).where(*filters)
    )
    if not total:
        return None
    if total == 1:
        return 100.0

    slower = await session.scalar(
        select(func.count())
        .select_from(UserCompletion)
        .where(
            *filters,
            UserCompletion.time_taken_seconds > time_taken_seconds,
        )
    )
    return 100.0 * float(slower or 0) / float(total)
