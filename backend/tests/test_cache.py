"""Tests for cache invalidation."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.cache import invalidate_search_cache


@pytest.mark.asyncio
async def test_invalidate_no_redis():
    """No-op when Redis not configured."""
    with patch("app.services.cache._client", None):
        result = await invalidate_search_cache()
        assert result == 0


@pytest.mark.asyncio
async def test_invalidate_deletes_search_keys():
    """Deletes all search:* keys and returns count."""
    mock_client = AsyncMock()

    async def fake_scan_iter(pattern, count=100):
        for key in ["search:abc123", "search:def456"]:
            yield key

    mock_client.scan_iter = fake_scan_iter
    mock_client.delete = AsyncMock(return_value=2)

    with patch("app.services.cache._client", mock_client):
        result = await invalidate_search_cache()
        assert result == 2
        mock_client.delete.assert_called_once_with("search:abc123", "search:def456")


@pytest.mark.asyncio
async def test_invalidate_no_keys():
    """Returns 0 when no search keys exist."""
    mock_client = AsyncMock()

    async def fake_scan_iter(pattern, count=100):
        return
        yield

    mock_client.scan_iter = fake_scan_iter

    with patch("app.services.cache._client", mock_client):
        result = await invalidate_search_cache()
        assert result == 0


@pytest.mark.asyncio
async def test_invalidate_redis_error():
    """Returns 0 on Redis error (silent failure)."""
    mock_client = AsyncMock()

    async def failing_scan(*args, **kwargs):
        raise ConnectionError("Redis down")
        yield

    mock_client.scan_iter = failing_scan

    with patch("app.services.cache._client", mock_client):
        result = await invalidate_search_cache()
        assert result == 0
