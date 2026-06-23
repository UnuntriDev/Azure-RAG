"""Integration tests: GET /api/prompts."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_prompts(client: AsyncClient):
    resp = await client.get("/api/prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    ids = {p["id"] for p in data}
    assert "v1" in ids
    assert "v2" in ids
    default_count = sum(1 for p in data if p.get("default"))
    assert default_count == 1
