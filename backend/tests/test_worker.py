"""Tests for the Redis-based ingestion queue (app.worker)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.worker import QUEUE_KEY, enqueue_ingestion


class TestEnqueueIngestion:
    async def test_returns_false_when_redis_unavailable(self):
        with patch("app.services.cache._client", None):
            result = await enqueue_ingestion(uuid.uuid4())
        assert result is False

    async def test_pushes_to_queue_when_redis_available(self):
        mock_client = AsyncMock()
        with patch("app.services.cache._client", mock_client):
            doc_id = uuid.uuid4()
            result = await enqueue_ingestion(doc_id)

        assert result is True
        mock_client.lpush.assert_awaited_once_with(QUEUE_KEY, str(doc_id))

    async def test_returns_false_on_redis_error(self):
        mock_client = AsyncMock()
        mock_client.lpush.side_effect = ConnectionError("gone")
        with patch("app.services.cache._client", mock_client):
            result = await enqueue_ingestion(uuid.uuid4())
        assert result is False
