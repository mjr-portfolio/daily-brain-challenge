from pydantic import ValidationError

from app.core.config import (
    DEV_JWT_SECRET,
    LOCAL_CORS_ORIGINS,
    Settings,
    normalize_database_url,
)


def test_normalize_database_url_rewrites_railway_schemes() -> None:
    assert (
        normalize_database_url("postgres://puzzle:puzzle@db:5432/puzzle")
        == "postgresql+asyncpg://puzzle:puzzle@db:5432/puzzle"
    )
    assert (
        normalize_database_url("postgresql://puzzle:puzzle@db:5432/puzzle")
        == "postgresql+asyncpg://puzzle:puzzle@db:5432/puzzle"
    )
    unchanged = "postgresql+asyncpg://puzzle:puzzle@localhost:5432/puzzle"
    assert normalize_database_url(unchanged) == unchanged


def _production(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "production",
        "JWT_SECRET": "a-real-production-secret-value",
        "DATABASE_URL": "postgresql://puzzle:puzzle@db:5432/puzzle",
        "CORS_ORIGINS": "https://play.example.com",
        "COOKIE_SECURE": True,
        "COOKIE_SAMESITE": "none",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_settings_rewrite_database_url() -> None:
    settings = _production()
    assert settings.DATABASE_URL == "postgresql+asyncpg://puzzle:puzzle@db:5432/puzzle"


def test_production_rejects_dev_jwt_secret() -> None:
    try:
        _production(JWT_SECRET=DEV_JWT_SECRET)
    except ValidationError as exc:
        assert "JWT_SECRET" in str(exc)
    else:
        raise AssertionError("dev JWT secret was accepted in production")


def test_production_rejects_samesite_none_without_secure() -> None:
    try:
        _production(COOKIE_SECURE=False)
    except ValidationError as exc:
        assert "COOKIE_SECURE" in str(exc)
    else:
        raise AssertionError("SameSite=None without Secure was accepted")


def test_production_rejects_localhost_and_empty_cors() -> None:
    for origins in (LOCAL_CORS_ORIGINS, "", "   "):
        try:
            _production(CORS_ORIGINS=origins)
        except ValidationError as exc:
            assert "CORS_ORIGINS" in str(exc)
        else:
            raise AssertionError(f"CORS_ORIGINS {origins!r} was accepted in production")


def test_development_keeps_local_defaults() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="development",
        JWT_SECRET=DEV_JWT_SECRET,
        CORS_ORIGINS=LOCAL_CORS_ORIGINS,
        COOKIE_SECURE=False,
        COOKIE_SAMESITE="lax",
    )
    assert settings.is_development
    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
