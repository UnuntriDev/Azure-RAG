"""Shared fixtures: async test client with in-memory SQLite DB."""

import uuid as _uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import MetaData, event, schema
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from app.db.models import Base


# ── SQLite compat: JSONB → JSON ──
@compiles(JSONB, "sqlite")
def _jsonb_as_json(type_, compiler, **kw):
    return "JSON"


_patched = False


def _sqlite_safe_tables(metadata: MetaData) -> None:
    """Patch Postgres-only server_defaults so CREATE TABLE works on SQLite."""
    global _patched
    if _patched:
        return
    _patched = True

    for table in metadata.tables.values():
        for col in table.columns:
            sd = col.server_default
            if sd is None:
                continue
            txt = str(sd.arg) if hasattr(sd, "arg") else ""
            if "gen_random_uuid" in txt:
                col.server_default = None
                if col.default is None:
                    col.default = schema.ColumnDefault(_uuid.uuid4)
            elif "::jsonb" in txt or "'pending'" in txt or "'v1'" in txt:
                col.server_default = None


@pytest.fixture()
async def _engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _sqlite_safe_tables(Base.metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture()
async def db_session(_engine) -> AsyncGenerator[AsyncSession, None]:
    """Session for inserting test data."""
    factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest.fixture()
async def client(_engine, db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX async test client with DB + Azure service mocks injected."""
    with (
        patch("app.auth.AUTH_ENABLED", False),
        patch("app.auth._s", MagicMock(google_client_id="")),
        patch("app.rate_limit.limiter", MagicMock(limit=lambda *a, **kw: lambda fn: fn)),
    ):
        from app.db.session import get_db
        from app.dependencies import get_blob_service, get_search_client
        from app.main import create_app

        app = create_app()

        # Endpoint gets its own session (separate identity map, same underlying DB via StaticPool).
        endpoint_factory = async_sessionmaker(_engine, expire_on_commit=True, class_=AsyncSession)

        async def override_db():
            async with endpoint_factory() as session:
                yield session

        mock_blob = MagicMock()
        mock_blob_client = AsyncMock()
        mock_blob.get_blob_client.return_value = mock_blob_client
        mock_blob.create_container = AsyncMock()
        mock_search = AsyncMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_blob_service] = lambda: mock_blob
        app.dependency_overrides[get_search_client] = lambda: mock_search

        mock_openai = AsyncMock()

        app.state.blob_client = mock_blob
        app.state.search_client = mock_search
        app.state.openai_client = mock_openai

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        app.dependency_overrides.clear()
