from datetime import date

from pydantic import BaseModel, EmailStr, Field


class TokenRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountRead(BaseModel):
    email: str
    streak: int
    total_score: int


class StreakAdopt(BaseModel):
    count: int = Field(ge=0)
    last_date: date | None = None
