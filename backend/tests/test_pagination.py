"""Tests for cursor pagination helpers and end-to-end cursor flow."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document
from app.pagination import decode_cursor, encode_cursor


class TestCursorEncodeDecode:
    def test_round_trip(self):
        ts = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        rid = uuid.uuid4()
        cursor = encode_cursor(ts, rid)
        ts2, rid2 = decode_cursor(cursor)
        assert ts2 == ts
        assert rid2 == rid

    def test_invalid_cursor_raises(self):
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor("not-a-valid-cursor!!!")

    def test_naive_timestamp_preserved(self):
        ts = datetime(2025, 1, 1, 0, 0, 0)
        rid = uuid.uuid4()
        cursor = encode_cursor(ts, rid)
        ts2, _ = decode_cursor(cursor)
        assert ts2.tzinfo is None


class TestDocumentsPagination:
    async def _insert_docs(self, db: AsyncSession, count: int) -> list[Document]:
        # All within the SAME second, distinct only by microseconds — this is the
        # exact case the old cursor (second-precision strftime) silently dropped.
        base = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        docs = []
        for i in range(count):
            doc = Document(
                id=uuid.uuid4(),
                filename=f"doc_{i:03d}.pdf",
                blob_url=f"https://blob.test/doc_{i}.pdf",
                status="indexed",
                chunk_count=1,
                created_at=base + timedelta(microseconds=i * 100_000),
            )
            db.add(doc)
            docs.append(doc)
        await db.commit()
        for d in docs:
            await db.refresh(d)
        return docs

    @pytest.mark.asyncio
    async def test_first_page_returns_next_cursor(self, client: AsyncClient, db_session: AsyncSession):
        await self._insert_docs(db_session, 5)
        resp = await client.get("/api/documents?limit=3")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 3
        assert body["next_cursor"] is not None

    @pytest.mark.asyncio
    async def test_second_page_via_cursor(self, client: AsyncClient, db_session: AsyncSession):
        await self._insert_docs(db_session, 5)
        resp1 = await client.get("/api/documents?limit=3")
        cursor = resp1.json()["next_cursor"]

        resp2 = await client.get(f"/api/documents?limit=3&cursor={cursor}")
        body2 = resp2.json()
        assert len(body2["items"]) == 2
        assert body2["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_no_overlap_between_pages(self, client: AsyncClient, db_session: AsyncSession):
        await self._insert_docs(db_session, 7)
        resp1 = await client.get("/api/documents?limit=4")
        page1_ids = {d["id"] for d in resp1.json()["items"]}
        cursor = resp1.json()["next_cursor"]

        resp2 = await client.get(f"/api/documents?limit=4&cursor={cursor}")
        page2_ids = {d["id"] for d in resp2.json()["items"]}

        assert page1_ids.isdisjoint(page2_ids)
        assert len(page1_ids) + len(page2_ids) == 7

    @pytest.mark.asyncio
    async def test_last_page_no_cursor(self, client: AsyncClient, db_session: AsyncSession):
        await self._insert_docs(db_session, 2)
        resp = await client.get("/api/documents?limit=10")
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["next_cursor"] is None
