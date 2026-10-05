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

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
