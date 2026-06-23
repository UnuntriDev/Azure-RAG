"""Tests for SecurityHeadersMiddleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    """All security headers added to every response."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in resp.headers["Permissions-Policy"]


@pytest.mark.asyncio
async def test_no_redirect_by_default(client: AsyncClient):
    """HTTPS redirect is off by default (local dev)."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_https_redirect_when_enabled():
    """When redirect=True and x-forwarded-proto is http, return 301."""
    from unittest.mock import MagicMock, patch

    with (
        patch("app.auth.AUTH_ENABLED", False),
        patch("app.auth._s", MagicMock(google_client_id="")),
        patch("app.rate_limit.limiter", MagicMock(limit=lambda *a, **kw: lambda fn: fn)),
        patch("app.config.get_settings") as mock_settings,
    ):
        settings = MagicMock()
        settings.cors_origins_list = ["http://localhost:3000"]
        settings.https_redirect = True
        settings.applicationinsights_connection_string = ""
        settings.redis_url = ""
        settings.azure_openai_endpoint = ""
        settings.azure_openai_api_key = ""
        settings.azure_openai_api_version = "2024-10-21"
        settings.azure_openai_chat_deployment = "gpt-4o-mini"
        settings.azure_search_endpoint = ""
        settings.azure_search_api_key = ""
        settings.azure_search_index_name = "rag-chunks"
        settings.azure_storage_connection_string = ""
        settings.azure_storage_container = "documents"
        mock_settings.return_value = settings

        from app.middleware import SecurityHeadersMiddleware
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from httpx import ASGITransport, AsyncClient as AC

        async def homepage(request):
            return PlainTextResponse("ok")

        test_app = Starlette(routes=[Route("/", homepage)])
        test_app.add_middleware(SecurityHeadersMiddleware, redirect=True)

        transport = ASGITransport(app=test_app)
        async with AC(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/", headers={"x-forwarded-proto": "http"}, follow_redirects=False)
            assert resp.status_code == 301
            assert resp.headers["location"].startswith("https://")

            resp2 = await ac.get("/", headers={"x-forwarded-proto": "https"})
            assert resp2.status_code == 200
