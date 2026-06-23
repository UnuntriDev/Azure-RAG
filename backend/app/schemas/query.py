import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    """One retrieved chunk surfaced to the UI (expandable fragment + score)."""

    document_id: uuid.UUID
    filename: str
    page: int
    location: str  # citation label (PDF "s. 5" / Excel "arkusz X, w. 10–60" / Word "sekcja: …")
    chunk_index: int
    score: float
    content: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    latency_ms: int


class QueryLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    answer: str
    sources: list[dict]
    latency_ms: int
    prompt_version: str
    created_at: datetime
