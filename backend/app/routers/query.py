import time

from azure.search.documents.aio import SearchClient
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Request
from app.auth import auth_deps, get_current_user
from app.config import Settings, get_settings
from app.rate_limit import QUERY_LIMIT, limiter
from app.db.models import QueryLog
from app.db.session import get_db
from app.dependencies import get_openai_client, get_search_client
from app.pagination import apply_cursor, encode_cursor
from app.schemas.pagination import CursorPage
from app.schemas.query import QueryLogRead, QueryRequest, QueryResponse, Source
from app.services.generation.generator import generate_answer
from app.services.generation.prompts import NOT_FOUND_MESSAGE, PROMPT_VERSION
from app.services.retrieval.retriever import hybrid_search
from openai import AsyncAzureOpenAI

router = APIRouter(prefix="/api/query", tags=["query"], dependencies=auth_deps())


@router.post("", response_model=QueryResponse)
@limiter.limit(QUERY_LIMIT)
async def query(
    request: Request,
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
    search: SearchClient = Depends(get_search_client),
    openai_client: AsyncAzureOpenAI = Depends(get_openai_client),
    settings: Settings = Depends(get_settings),
    user_id: str | None = Depends(get_current_user),
) -> QueryResponse:
    start = time.perf_counter()

    chunks = await hybrid_search(
        search, openai_client, settings.azure_openai_embedding_deployment, req.question,
        semantic_config=settings.azure_search_semantic_config or None,
    )
    if chunks:
        answer = await generate_answer(
            openai_client, settings.azure_openai_chat_deployment, req.question, chunks
        )
    else:
        answer = NOT_FOUND_MESSAGE

    latency_ms = int((time.perf_counter() - start) * 1000)
    sources = [Source(**c) for c in chunks]

    # Log every query — the stage-3 eval set is built from this table.
    db.add(
        QueryLog(
            user_id=user_id,
            question=req.question,
            answer=answer,
            sources=[s.model_dump(mode="json") for s in sources],
            prompt_version=PROMPT_VERSION,
            latency_ms=latency_ms,
        )
    )
    await db.commit()

    return QueryResponse(answer=answer, sources=sources, latency_ms=latency_ms)


@router.get("/logs", response_model=CursorPage[QueryLogRead])
async def query_logs(
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user),
) -> dict:
    q = select(QueryLog)
    if user_id:
        q = q.where(QueryLog.user_id == user_id)
    q = apply_cursor(q, cursor=cursor, sort_column=QueryLog.created_at, id_column=QueryLog.id, limit=limit + 1)
    result = await db.execute(q)
    rows = list(result.scalars().all())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    return {"items": rows, "next_cursor": next_cursor}
