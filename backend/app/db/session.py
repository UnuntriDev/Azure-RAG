"""Async SQLAlchemy engine + session dependency."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_settings = get_settings()

# asyncpg needs ssl via connect_args, not ?sslmode= in the URL.
_connect_args = {"ssl": "require"} if _settings.db_ssl_require else {}

engine = create_async_engine(
    _settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — one session per request."""
    async with SessionLocal() as session:
        yield session
