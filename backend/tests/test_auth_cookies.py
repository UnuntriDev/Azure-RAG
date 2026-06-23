"""Tests for HttpOnly cookie auth flow (login / logout / me + cookie-based request auth)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import ASGITransport, AsyncClient

from app.auth import SESSION_COOKIE


FAKE_PAYLOAD = {
    "sub": "google-uid-123",
    "name": "Test User",
    "email": "test@example.com",
    "picture": "https://example.com/photo.jpg",
    "aud": "fake-client-id",
    "iss": "accounts.google.com",
    "exp": 9999999999,
}


@pytest.fixture()
async def auth_client(_engine):
    """Client with auth ENABLED and Google verification mocked."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    with (
        patch("app.auth.AUTH_ENABLED", True),
        patch("app.auth._s", MagicMock(google_client_id="fake-client-id")),
        patch("app.routers.auth_routes.AUTH_ENABLED", True),
        patch("app.rate_limit.limiter", MagicMock(limit=lambda *a, **kw: lambda fn: fn)),
    ):
        from app.db.session import get_db
        from app.dependencies import get_blob_service, get_search_client
        from app.main import create_app

        app = create_app()

        factory = async_sessionmaker(_engine, expire_on_commit=True, class_=AsyncSession)

        async def override_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_blob_service] = lambda: MagicMock()
        app.dependency_overrides[get_search_client] = lambda: AsyncMock()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        app.dependency_overrides.clear()


def _mock_verify(token, transport, audience):
    if token == "valid-google-token":
        return FAKE_PAYLOAD
    raise ValueError("Invalid token")


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_sets_cookie_and_returns_user(self, auth_client: AsyncClient):
        with patch("app.auth.id_token.verify_oauth2_token", side_effect=_mock_verify):
            resp = await auth_client.post(
                "/api/auth/login",
                json={"id_token": "valid-google-token"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["sub"] == "google-uid-123"
        assert body["name"] == "Test User"
        assert body["email"] == "test@example.com"

        cookies = resp.cookies
        assert SESSION_COOKIE in cookies
        assert cookies[SESSION_COOKIE] == "valid-google-token"

    @pytest.mark.asyncio
    async def test_login_rejects_invalid_token(self, auth_client: AsyncClient):
        with patch("app.auth.id_token.verify_oauth2_token", side_effect=_mock_verify):
            resp = await auth_client.post(
                "/api/auth/login",
                json={"id_token": "bad-token"},
            )
        assert resp.status_code == 401


class TestLogoutEndpoint:
    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/auth/logout")
        assert resp.status_code == 204
        set_cookie = resp.headers.get("set-cookie", "")
        assert SESSION_COOKIE in set_cookie


class TestMeEndpoint:
    @pytest.mark.asyncio
    async def test_me_returns_user_with_valid_cookie(self, auth_client: AsyncClient):
        with patch("app.auth.id_token.verify_oauth2_token", side_effect=_mock_verify):
            auth_client.cookies.set(SESSION_COOKIE, "valid-google-token")
            resp = await auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["sub"] == "google-uid-123"

    @pytest.mark.asyncio
    async def test_me_returns_401_without_cookie(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/auth/me")
        assert resp.status_code == 401


class TestCookieAuth:
    @pytest.mark.asyncio
    async def test_request_with_cookie_is_authorized(self, auth_client: AsyncClient):
        with patch("app.auth.id_token.verify_oauth2_token", side_effect=_mock_verify):
            auth_client.cookies.set(SESSION_COOKIE, "valid-google-token")
            resp = await auth_client.get("/api/documents")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_request_without_credentials_returns_401(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/documents")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_bearer_fallback_still_works(self, auth_client: AsyncClient):
        with patch("app.auth.id_token.verify_oauth2_token", side_effect=_mock_verify):
            resp = await auth_client.get(
                "/api/documents",
                headers={"Authorization": "Bearer valid-google-token"},
            )
        assert resp.status_code == 200
