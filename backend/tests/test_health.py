"""Tests for /api/health and /api/ready endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_ok(client: AsyncClient):
    resp = await client.get("/api/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["postgres"] == "ok"
    assert data["redis"] in ("ok", "not_configured")


@pytest.mark.asyncio
async def test_readiness_has_all_fields(client: AsyncClient):
    resp = await client.get("/api/ready")
    data = resp.json()
    assert "status" in data
    assert "postgres" in data
    assert "redis" in data
