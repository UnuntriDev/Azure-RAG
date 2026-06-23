"""Integration tests: GET /api/query/logs."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import QueryLog


async def _insert_log(db: AsyncSession, *, question: str = "test?", user_id: str | None = None):
    log = QueryLog(
        id=uuid.uuid4(),
        user_id=user_id,
        question=question,
        answer="answer",
        sources=[],
        prompt_version="v1",
        latency_ms=100,
    )
    db.add(log)
    await db.commit()


@pytest.mark.asyncio
async def test_query_logs_empty(client: AsyncClient):
    resp = await client.get("/api/query/logs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["next_cursor"] is None


@pytest.mark.asyncio
async def test_query_logs_returns_data(client: AsyncClient, db_session: AsyncSession):
    await _insert_log(db_session, question="Q1")
    await _insert_log(db_session, question="Q2")
    resp = await client.get("/api/query/logs")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


@pytest.mark.asyncio
async def test_query_logs_limit(client: AsyncClient, db_session: AsyncSession):
    for i in range(10):
        await _insert_log(db_session, question=f"Q{i}")
    resp = await client.get("/api/query/logs?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3


@pytest.mark.asyncio
async def test_query_logs_limit_cap(client: AsyncClient):
    resp = await client.get("/api/query/logs?limit=9999")
    assert resp.status_code == 422  # validation error — le=200


@pytest.mark.asyncio
async def test_query_logs_limit_zero(client: AsyncClient):
    resp = await client.get("/api/query/logs?limit=0")
    assert resp.status_code == 422  # validation error — ge=1
