from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadinessResponse(BaseModel):
    status: str
    postgres: str
    redis: str
