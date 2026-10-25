from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.profile import PreferencesRead, clean_display_name


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None

    @field_validator("display_name")
    @classmethod
    def _display_name(cls, value: str | None) -> str | None:
        return clean_display_name(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccountRead(BaseModel):
    email: str
    display_name: str | None = None
    preferences: PreferencesRead
    streak: int
    total_score: int


class StreakAdopt(BaseModel):
    count: int = Field(ge=0)
    last_date: date | None = None


class StreakAdoptResult(AccountRead):
    applied: bool
