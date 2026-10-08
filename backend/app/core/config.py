from functools import lru_cache

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
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
