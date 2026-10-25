import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError

from app.core.config import get_settings


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or validated."""


def make_refresh_token() -> tuple[str, str, datetime]:
    """Return the raw token, its sha256 hex digest, and the expiry."""
    settings = get_settings()
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    expires = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    return raw, digest, expires


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub = payload.get("sub")
        if not sub:
            raise TokenError("Token missing subject")
        return UUID(str(sub))
    except (InvalidTokenError, ValueError, TypeError) as exc:
        raise TokenError("Invalid token") from exc
