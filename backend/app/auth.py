"""Google OAuth2 authentication via ID token verification.

Enable by setting GOOGLE_CLIENT_ID.
Leave empty for local dev — every request is allowed as anonymous.

Supports two credential sources (checked in order):
1. HttpOnly session cookie (set by POST /api/auth/login)
2. Authorization: Bearer <token> header (curl / Postman fallback)

Usage in routers:
    from app.auth import auth_deps
    router = APIRouter(prefix="/api/foo", dependencies=auth_deps())
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from starlette.concurrency import run_in_threadpool

from app.config import get_settings

_s = get_settings()

AUTH_ENABLED: bool = bool(_s.google_client_id)

SESSION_COOKIE = "session"

_bearer = HTTPBearer(auto_error=False)
_transport = google_requests.Request()


async def _try_verify(token: str) -> dict | None:
    """Verify a Google ID token → claims, or None if it doesn't validate. The single
    verification primitive — every code path (dependency, login, me) goes through here."""
    try:
        return await run_in_threadpool(
            id_token.verify_oauth2_token,
            token,
            _transport,
            _s.google_client_id,
        )
    except Exception:
        return None


async def verify_id_token(token: str) -> dict:
    """Verify a token, raising HTTP 401 on failure. Used by the auth router."""
    payload = await _try_verify(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


async def _verify_google_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    if not AUTH_ENABLED:
        return None
    # Try every credential source — a stale/expired cookie must not shadow a valid
    # Bearer header (curl/Postman) and vice-versa.
    candidates: list[str] = []
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        candidates.append(cookie)
    if credentials:
        candidates.append(credentials.credentials)
    if not candidates:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    for token in candidates:
        payload = await _try_verify(token)
        if payload is not None:
            return payload
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def auth_deps() -> list:
    """Returns [Depends(_verify_google_token)] when auth is enabled, else []."""
    if AUTH_ENABLED:
        return [Depends(_verify_google_token)]
    return []


async def get_current_user(
    payload: dict | None = Depends(_verify_google_token),
) -> str | None:
    """Returns the Google 'sub' claim (stable user ID), or None in local dev."""
    if payload is None:
        return None
    return payload.get("sub") or None
