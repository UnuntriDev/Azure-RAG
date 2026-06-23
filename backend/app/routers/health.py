from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services import cache

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, status_code=200)
async def health() -> HealthResponse:
    """Liveness probe — intentionally does NOT touch the DB."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse, status_code=200)
async def readiness(db: AsyncSession = Depends(get_db)) -> ReadinessResponse:
    """Readiness probe — checks PostgreSQL and Redis connectivity."""
    pg_status = "ok"
    redis_status = "ok"

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        pg_status = "unavailable"

    if cache._client is not None:
        try:
            await cache._client.ping()
        except Exception:
            redis_status = "unavailable"
    else:
        redis_status = "not_configured"

    overall = "ok" if pg_status == "ok" and redis_status in ("ok", "not_configured") else "degraded"

    return ReadinessResponse(status=overall, postgres=pg_status, redis=redis_status)
