from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import get_settings

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class TrustedOriginMiddleware:
    """Reject cookie-bearing writes from a page we did not list.

    Browsers omit Origin on same-origin GET and on non-browser clients such as
    pytest. A present Origin that is not in CORS_ORIGINS is a cross-site write,
    which SameSite=None would otherwise accept.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in UNSAFE_METHODS:
            origin = _header(scope, b"origin")
            allowed = set(get_settings().cors_origin_list)
            if origin is not None and origin not in allowed:
                response = JSONResponse({"detail": "Origin not allowed"}, status_code=403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope["headers"]:
        if key.lower() == name:
            return value.decode()
    return None
