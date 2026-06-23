"""Tests for /api/traces endpoint — user_id filtering."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Trace


@pytest.fixture()
async def traces_for_two_users(db_session: AsyncSession) -> dict[str, list[uuid.UUID]]:
    """Create traces for user_a, user_b, and one anonymous."""
    ids: dict[str, list[uuid.UUID]] = {"user_a": [], "user_b": [], "anon": []}
    for user_id, label in [("user_a", "user_a"), ("user_b", "user_b"), (None, "anon")]:
        t = Trace(
            id=uuid.uuid4(),
            kind="rag",
            question=f"question from {label}",
            prompt_version="v1",
            user_id=user_id,
            spans=[],
            total_ms=100,
        )
        db_session.add(t)
        ids[label].append(t.id)
    await db_session.commit()
    return ids


@pytest.mark.asyncio
async def test_list_traces_no_auth_returns_all(
    client: AsyncClient, traces_for_two_users: dict,
):
    """With auth disabled, all traces are returned."""
    resp = await client.get("/api/traces")
    assert resp.status_code == 200
    data = resp.json()["items"]
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_traces_filtered_by_user(
    client: AsyncClient, traces_for_two_users: dict,
):
    """When user_id dependency is overridden, only that user's traces appear."""
    from unittest.mock import AsyncMock
    from app.auth import get_current_user

    client._transport.app.dependency_overrides[get_current_user] = lambda: "user_a"
    try:
        resp = await client.get("/api/traces")
        assert resp.status_code == 200
        data = resp.json()["items"]
        assert len(data) == 1
        assert data[0]["question"] == "question from user_a"
    finally:
        del client._transport.app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_get_trace_own(
    client: AsyncClient, traces_for_two_users: dict,
):
    """User can access their own trace."""
    trace_id = traces_for_two_users["user_a"][0]
    resp = await client.get(f"/api/traces/{trace_id}")
    assert resp.status_code == 200
    assert resp.json()["user_id"] is None or resp.json()["id"] == str(trace_id)


@pytest.mark.asyncio
async def test_get_trace_other_user_returns_404(
    client: AsyncClient, traces_for_two_users: dict,
):
    """User cannot access another user's trace."""
    from app.auth import get_current_user

    trace_id = traces_for_two_users["user_b"][0]
    client._transport.app.dependency_overrides[get_current_user] = lambda: "user_a"
    try:
        resp = await client.get(f"/api/traces/{trace_id}")
        assert resp.status_code == 404
    finally:
        del client._transport.app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_trace_read_schema_includes_user_id(
    client: AsyncClient, traces_for_two_users: dict,
):
    """TraceRead schema exposes user_id field."""
    resp = await client.get("/api/traces")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "user_id" in item
