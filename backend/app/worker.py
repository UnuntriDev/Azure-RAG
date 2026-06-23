"""Async task worker — pulls ingestion jobs from Redis queue.

Run: python -m app.worker

Uses BRPOP on a Redis list — simple, reliable, no extra dependencies.
Falls back gracefully: if Redis is unavailable, documents.py uses BackgroundTask instead.
"""

import asyncio
import json
import uuid

import structlog

from app.config import get_settings
from app.logging_config import configure_logging
from app.services.cache import init_redis, close_redis
from app.services.ingestion.indexer import ingest_document

QUEUE_KEY = "ingestion:queue"

logger = structlog.get_logger()


async def enqueue_ingestion(document_id: uuid.UUID) -> bool:
    """Push a document_id onto the Redis ingestion queue. Returns False if Redis unavailable."""
    from app.services.cache import _client

    if _client is None:
        return False
    try:
        await _client.lpush(QUEUE_KEY, str(document_id))
        return True
    except Exception:
        return False


async def _process_one(raw: str) -> None:
    try:
        document_id = uuid.UUID(raw)
    except ValueError:
        logger.error("invalid_task_payload", raw=raw)
        return

    logger.info("task_start", document_id=str(document_id))
    await ingest_document(document_id)
    logger.info("task_done", document_id=str(document_id))


async def run_worker() -> None:
    configure_logging()
    settings = get_settings()

    if not settings.redis_url:
        logger.error("worker_no_redis", detail="REDIS_URL is required for the worker process")
        return

    import redis.asyncio as aioredis

    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    await client.ping()
    logger.info("worker_started", queue=QUEUE_KEY)

    try:
        while True:
            result = await client.brpop(QUEUE_KEY, timeout=5)
            if result is None:
                continue
            _, raw = result
            await _process_one(raw)
    except asyncio.CancelledError:
        logger.info("worker_stopping")
    finally:
        await client.aclose()
        logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(run_worker())
