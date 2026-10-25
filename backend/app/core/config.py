from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "project-play"
    APP_ENV: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://puzzle:puzzle@localhost:5432/puzzle"
    JWT_SECRET: str = "dev-only-change-me-use-32+chars!!"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 30
    # Comma-separated page origins allowed to call the API with cookies.
    # Production: the exact Vercel URL, for example https://your-project.vercel.app
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Production behind Railway + Vercel: COOKIE_SECURE=true and COOKIE_SAMESITE=none.
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash-lite"
    # A bad puzzle retries GEMINI_MODEL immediately, then waits and tries GEMINI_FALLBACK_MODEL.
    # Rate limits, timeouts, and server errors wait, retry the same model once, then wait and try the fallback.

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
