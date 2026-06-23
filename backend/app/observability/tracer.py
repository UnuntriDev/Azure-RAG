"""Per-request tracing: collects spans and persists them to the traces table."""

import time

import structlog

from app.db.models import Trace

logger = structlog.get_logger()


class Tracer:
    def __init__(self, kind: str, question: str, prompt_version: str, user_id: str | None = None):
        self.kind = kind
        self.question = question
        self.prompt_version = prompt_version
        self.user_id = user_id
        self.correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
        self.spans: list[dict] = []
        self._t0 = time.perf_counter()

    def add(self, name: str, duration_ms: int, **meta) -> None:
        """Append a span and emit a structlog event."""
        self.spans.append({"name": name, "duration_ms": duration_ms, "meta": meta})
        logger.info("span", span=name, duration_ms=duration_ms, **meta)

    @property
    def total_ms(self) -> int:
        return int((time.perf_counter() - self._t0) * 1000)

    def to_model(self) -> Trace:
        return Trace(
            correlation_id=self.correlation_id,
            kind=self.kind,
            question=self.question,
            prompt_version=self.prompt_version,
            user_id=self.user_id,
            spans=self.spans,
            total_ms=self.total_ms,
        )
