import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TraceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    correlation_id: str | None
    kind: str
    question: str
    prompt_version: str
    user_id: str | None
    spans: list[dict]
    total_ms: int
    created_at: datetime
