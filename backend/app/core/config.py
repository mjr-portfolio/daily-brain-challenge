from functools import lru_cache
from typing import Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-change-me-use-32+chars!!"
LOCAL_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def normalize_database_url(url: str) -> str:
    """Railway Postgres URLs use postgres:// or postgresql://. The app needs asyncpg."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    return url


def _origin_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "project-play"
    APP_ENV: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://puzzle:puzzle@localhost:5432/puzzle"
    JWT_SECRET: str = DEV_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 30
    # Comma-separated page origins allowed to call the API with cookies.
    # Production: the exact Vercel URL, for example https://your-project.vercel.app
    CORS_ORIGINS: str = LOCAL_CORS_ORIGINS
    # Production (Vercel /api rewrite → Railway): COOKIE_SECURE=true, COOKIE_SAMESITE=lax.
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash-lite"
    # A bad puzzle retries GEMINI_MODEL immediately, then waits and tries GEMINI_FALLBACK_MODEL.
    # Rate limits, timeouts, and server errors wait, retry the same model once, then wait and try the fallback.

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_asyncpg_driver(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    @model_validator(mode="after")
    def _refuse_unsafe_production_settings(self) -> Self:
        if self.is_development:
            return self
        if self.JWT_SECRET == DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be changed when APP_ENV is not development")
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
        origins = set(self.cors_origin_list)
        if not origins or origins == _origin_set(LOCAL_CORS_ORIGINS):
            raise ValueError(
                "CORS_ORIGINS must be the production page origin when APP_ENV is not development"
            )
        return self

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
