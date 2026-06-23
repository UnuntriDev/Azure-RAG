import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None
    # Agent mode (LangGraph + tools) is the stage-2 default; set false for classic single-shot RAG.
    agent: bool = True
    # Answer-style prompt version (see prompts.PROMPT_VERSIONS); falls back to default if unknown.
    prompt_version: str = "v1"
    # Optional list of document UUIDs to scope retrieval — None means search all documents.
    document_ids: list[uuid.UUID] | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    sources: list[dict] | None = None
    latency_ms: int | None = None
    created_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead] = []
