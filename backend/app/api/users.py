from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.stats import UserStatsRead
from app.services.stats import user_stats

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/stats", response_model=UserStatsRead)
async def read_my_stats(db: DbSession, user: CurrentUser) -> UserStatsRead:
    return await user_stats(db, user, datetime.now(UTC).date())
