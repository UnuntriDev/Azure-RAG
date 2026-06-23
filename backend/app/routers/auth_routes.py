"""Login / logout / me — exchanges a Google ID token for an HttpOnly session cookie."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.auth import AUTH_ENABLED, SESSION_COOKIE, verify_id_token
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    id_token: str


class UserInfo(BaseModel):
    sub: str
    name: str
    email: str
    picture: str


def _user_info(payload: dict) -> UserInfo:
    return UserInfo(
        sub=payload.get("sub", ""),
        name=payload.get("name", payload.get("email", "User")),
        email=payload.get("email", ""),
        picture=payload.get("picture", ""),
    )


def _set_session_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=s.cookie_secure,
        samesite=s.cookie_samesite,
        domain=s.cookie_domain or None,
        path="/api",
        max_age=3600,
    )


def _clear_session_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=s.cookie_secure,
        samesite=s.cookie_samesite,
        domain=s.cookie_domain or None,
        path="/api",
    )


@router.post("/login", response_model=UserInfo)
async def login(body: LoginRequest, response: Response) -> UserInfo:
    if not AUTH_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth disabled")

    payload = await verify_id_token(body.id_token)
    _set_session_cookie(response, body.id_token)
    return _user_info(payload)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    _clear_session_cookie(response)


@router.get("/me", response_model=UserInfo)
async def me(request: Request) -> UserInfo:
    if not AUTH_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth disabled")

    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = await verify_id_token(token)
    return _user_info(payload)
