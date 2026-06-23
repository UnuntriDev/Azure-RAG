"""Expose the available answer-style prompt versions so the UI can render a selector."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth import auth_deps
from app.services.generation.prompts import PROMPT_VERSION, PROMPT_VERSIONS

router = APIRouter(prefix="/api/prompts", tags=["prompts"], dependencies=auth_deps())


class PromptVersion(BaseModel):
    id: str
    label: str
    description: str
    default: bool


@router.get("", response_model=list[PromptVersion])
async def list_prompt_versions() -> list[PromptVersion]:
    return [
        PromptVersion(
            id=vid,
            label=meta["label"],
            description=meta["description"],
            default=(vid == PROMPT_VERSION),
        )
        for vid, meta in PROMPT_VERSIONS.items()
    ]
