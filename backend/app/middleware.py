"""Per-request correlation id + access logging (DoD: correlation_id per request)."""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

logger = structlog.get_logger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds HSTS + security headers. Optionally redirects HTTP → HTTPS."""

    def __init__(self, app, redirect: bool = False):
        super().__init__(app)
        self.redirect = redirect

    async def dispatch(self, request: Request, call_next):
        if self.redirect:
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            if proto == "http":
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(url), status_code=301)

        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed")
            raise

        response.headers["X-Correlation-ID"] = correlation_id
        logger.info(
            "request_completed",
            status_code=response.status_code,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )
        return response
