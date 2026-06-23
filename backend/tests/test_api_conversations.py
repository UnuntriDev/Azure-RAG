"""Integration tests: /api/chat conversation CRUD (not the SSE stream)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message


async def _insert_conv(
    db: AsyncSession,
    *,
    title: str = "Test conv",
    user_id: str | None = None,
    with_messages: int = 0,
) -> Conversation:
    conv = Conversation(id=uuid.uuid4(), title=title, user_id=user_id)
    db.add(conv)
    await db.flush()
    for i in range(with_messages):
        role = "user" if i % 2 == 0 else "assistant"
        db.add(Message(conversation_id=conv.id, role=role, content=f"msg {i}"))
    await db.commit()
    await db.refresh(conv)
    return conv


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient):
    resp = await client.get("/api/chat")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["next_cursor"] is None


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, db_session: AsyncSession):
    await _insert_conv(db_session, title="First")
    await _insert_conv(db_session, title="Second")
    resp = await client.get("/api/chat")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


@pytest.mark.asyncio
async def test_get_conversation(client: AsyncClient, db_session: AsyncSession):
    conv = await _insert_conv(db_session, with_messages=4)
    resp = await client.get(f"/api/chat/{conv.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test conv"
    assert len(data["messages"]) == 4


@pytest.mark.asyncio
async def test_get_conversation_not_found(client: AsyncClient):
    resp = await client.get(f"/api/chat/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient, db_session: AsyncSession):
    conv = await _insert_conv(db_session, with_messages=2)
    resp = await client.delete(f"/api/chat/{conv.id}")
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/chat/{conv.id}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation_not_found(client: AsyncClient):
    resp = await client.delete(f"/api/chat/{uuid.uuid4()}")
    assert resp.status_code == 404
