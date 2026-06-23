from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.auth import AUTH_ENABLED
from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware
from app.observability.telemetry import setup_telemetry
from app.rate_limit import limiter
from app.routers import auth_routes, chat, documents, health, prompts, query, traces
from app.services.cache import close_redis, init_redis
from app.services.ingestion.embedder import make_openai_client
from app.services.storage.blob import make_blob_service_client
from app.services.storage.search import make_search_client

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()

    # Telemetry — must run before the first request; instrument_app adds ASGI middleware.
    ai_ok = setup_telemetry(settings.applicationinsights_connection_string)
    if ai_ok:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)

    redis_ok = False
    try:
        await init_redis(settings.redis_url)
        redis_ok = bool(settings.redis_url)
    except Exception:
        pass  # Redis not required — app works without it

    blob_client = make_blob_service_client(settings)
    search_client = make_search_client(settings)
    openai_client = make_openai_client(settings)
    app.state.blob_client = blob_client
    app.state.search_client = search_client
    app.state.openai_client = openai_client

    logger.info("startup", auth_enabled=AUTH_ENABLED, redis=redis_ok, app_insights=ai_ok)
    yield
    await openai_client.close()
    await search_client.close()
    await blob_client.close()
    await close_redis()
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Azure RAG Knowledge Assistant",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, redirect=settings.https_redirect)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(auth_routes.router)
    app.include_router(documents.router)
    app.include_router(query.router)
    app.include_router(chat.router)
    app.include_router(prompts.router)
    app.include_router(traces.router)
    return app


app = create_app()
