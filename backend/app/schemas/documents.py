import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: str
    chunk_count: int | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
