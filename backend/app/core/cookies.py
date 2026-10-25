from typing import Literal

from starlette.responses import Response

from app.core.config import get_settings
from app.schemas.auth import TokenResponse

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
# Only the refresh call needs the long-lived token. /api/auth would also send it to /me.
REFRESH_COOKIE_PATH = "/api/auth/refresh"
SameSite = Literal["lax", "strict", "none"]


def _flags() -> tuple[bool, SameSite]:
    settings = get_settings()
    return settings.COOKIE_SECURE, settings.COOKIE_SAMESITE


def attach_session(response: Response, tokens: TokenResponse) -> None:
    """Store both session tokens where page scripts cannot read them."""
    settings = get_settings()
    secure, samesite = _flags()
    response.set_cookie(
        ACCESS_COOKIE,
        tokens.access_token,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/api",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.JWT_REFRESH_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=REFRESH_COOKIE_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    secure, samesite = _flags()
    response.delete_cookie(
        ACCESS_COOKIE,
        path="/api",
        httponly=True,
        secure=secure,
        samesite=samesite,
    )
    for path in (REFRESH_COOKIE_PATH, "/api/auth"):
        response.delete_cookie(
            REFRESH_COOKIE,
            path=path,
            httponly=True,
            secure=secure,
            samesite=samesite,
        )
