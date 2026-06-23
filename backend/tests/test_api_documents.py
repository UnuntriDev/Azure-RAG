"""Integration tests: /api/documents endpoints."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document


async def _insert_doc(
    db: AsyncSession,
    *,
    filename: str = "test.pdf",
    status: str = "indexed",
    user_id: str | None = None,
    chunk_count: int | None = 5,
) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename=filename,
        blob_url="https://blob.test/test.pdf",
        status=status,
        user_id=user_id,
        chunk_count=chunk_count,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient):
    resp = await client.get("/api/documents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["next_cursor"] is None


@pytest.mark.asyncio
async def test_list_documents_with_data(client: AsyncClient, db_session: AsyncSession):
    await _insert_doc(db_session, filename="a.pdf")
    await _insert_doc(db_session, filename="b.pdf")
    resp = await client.get("/api/documents")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    filenames = {d["filename"] for d in items}
    assert filenames == {"a.pdf", "b.pdf"}


@pytest.mark.asyncio
async def test_get_document(client: AsyncClient, db_session: AsyncSession):
    doc = await _insert_doc(db_session)
    resp = await client.get(f"/api/documents/{doc.id}")
    assert resp.status_code == 200
    assert resp.json()["filename"] == "test.pdf"


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/documents/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_indexed(client: AsyncClient, db_session: AsyncSession):
    doc = await _insert_doc(db_session, status="indexed")
    resp = await client.delete(f"/api/documents/{doc.id}")
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/documents/{doc.id}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_processing_blocked(client: AsyncClient, db_session: AsyncSession):
    doc = await _insert_doc(db_session, status="processing")
    resp = await client.delete(f"/api/documents/{doc.id}")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_document_pending_blocked(client: AsyncClient, db_session: AsyncSession):
    doc = await _insert_doc(db_session, status="pending")
    resp = await client.delete(f"/api/documents/{doc.id}")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_document_not_found(client: AsyncClient):
    resp = await client.delete(f"/api/documents/{uuid.uuid4()}")
    assert resp.status_code == 404
