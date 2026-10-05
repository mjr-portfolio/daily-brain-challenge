from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DbSession
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def issue_token(payload: TokenRequest, db: DbSession) -> TokenResponse:
    email = payload.email.lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))
