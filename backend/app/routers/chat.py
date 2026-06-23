"""SSE streaming chat. Event protocol:
  - {"event": "conversation", "data": {"id": "..."}}        — fired once at start
  - {"event": "tool", "data": {"name": "search_documents"}} — tool invoked (agent mode)
  - {"event": "delta", "data": {"content": "tok"}}          — streamed token
  - {"event": "sources", "data": [<Source>, ...]}            — after generation
  - {"event": "done", "data": {"latency_ms": 123}}          — final
  - {"event": "error", "data": {"detail": "..."}}           — on failure
"""

import functools
import json
import logging
import time
import uuid

from azure.search.documents.aio import SearchClient
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import auth_deps, get_current_user
from app.config import Settings, get_settings
from app.db.models import Conversation, Message, QueryLog
from app.db.session import get_db
from app.rate_limit import CHAT_LIMIT, limiter
from app.dependencies import get_openai_client, get_search_client
from app.observability.tracer import Tracer
from app.pagination import apply_cursor, encode_cursor
from app.schemas.chat import ChatRequest, ConversationDetail, ConversationRead
from app.schemas.pagination import CursorPage
from app.schemas.query import Source
from fastapi import Request
from app.services.agent.graph import build_agent, make_chat_model
from app.services.agent.prompts import agent_prompt
from app.services.agent.tools import build_tools
from app.services.generation.generator import build_messages
from app.services.generation.prompts import (
    NOT_FOUND_MESSAGE,
    PROMPT_VERSION,
    PROMPT_VERSIONS,
    get_prompt,
)
from app.services.retrieval.retriever import hybrid_search
from openai import AsyncAzureOpenAI

router = APIRouter(prefix="/api/chat", tags=["chat"], dependencies=auth_deps())

MAX_HISTORY_TURNS = 10
MAX_HISTORY_TOKENS = 3000


@functools.cache
def _get_encoding():
    import tiktoken

    try:
        return tiktoken.encoding_for_model("gpt-4o-mini")
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def _sse(event: str, data: dict | list | str) -> str:
    payload = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    return f"event: {event}\ndata: {payload}\n\n"


def _history_from_messages(messages: list[Message]) -> list[dict]:
    """Convert DB messages into OpenAI format, newest first, capped by token budget."""
    enc = _get_encoding()
    history: list[dict] = []
    total = 0
    for m in reversed(messages[-(MAX_HISTORY_TURNS * 2) :]):
        tokens = len(enc.encode(m.content))
        if total + tokens > MAX_HISTORY_TOKENS:
            break
        history.insert(0, {"role": m.role, "content": m.content})
        total += tokens
    return history


def _dedupe_sources(chunks: list[dict]) -> list[Source]:
    """The agent may search several times → collapse duplicate chunks (same doc + index)."""
    seen: set[tuple] = set()
    out: list[Source] = []
    for c in chunks:
        key = (c["document_id"], c["chunk_index"])
        if key in seen:
            continue
        seen.add(key)
        out.append(Source(**c))
    return out


def _own_conv(conv: Conversation, user_id: str | None) -> bool:
    if not user_id or not conv.user_id:
        return True
    return conv.user_id == user_id


@router.post("")
@limiter.limit(CHAT_LIMIT)
async def chat(
    request: Request,
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    search: SearchClient = Depends(get_search_client),
    openai_client: AsyncAzureOpenAI = Depends(get_openai_client),
    settings: Settings = Depends(get_settings),
    user_id: str | None = Depends(get_current_user),
):
    # Resolve or create conversation
    if req.conversation_id:
        conv = await db.get(
            Conversation, req.conversation_id, options=[selectinload(Conversation.messages)]
        )
        if not conv or not _own_conv(conv, user_id):
            raise HTTPException(status_code=404, detail="Konwersacja nie istnieje.")
    else:
        conv = Conversation(user_id=user_id)
        db.add(conv)
        await db.flush()

    # Persist user message
    user_msg = Message(conversation_id=conv.id, role="user", content=req.question)
    db.add(user_msg)
    await db.flush()

    # Auto-title from first user message
    if conv.title is None:
        conv.title = req.question[:80]

    await db.commit()
    await db.refresh(conv, attribute_names=["messages"])

    history = _history_from_messages(conv.messages[:-1])
    version = req.prompt_version if req.prompt_version in PROMPT_VERSIONS else PROMPT_VERSION

    async def event_stream():
        start = time.perf_counter()
        tracer = Tracer(
            kind="agent" if req.agent else "rag",
            question=req.question,
            prompt_version=version,
            user_id=user_id,
        )
        try:
            yield _sse("conversation", {"id": str(conv.id)})

            doc_ids = [str(d) for d in req.document_ids] if req.document_ids else None

            if req.agent:
                sources_chunks: list[dict] = []
                tools = build_tools(search, openai_client, settings, sources_chunks, doc_ids)
                agent = build_agent(make_chat_model(settings), tools, agent_prompt(version))
                lc_messages = (history or []) + [{"role": "user", "content": req.question}]

                full_answer = ""
                agent_start = time.perf_counter()
                tool_starts: dict[str, tuple[str, float]] = {}
                async for ev in agent.astream_events({"messages": lc_messages}, version="v2"):
                    etype = ev["event"]
                    if etype == "on_tool_start":
                        tool_starts[ev["run_id"]] = (ev["name"], time.perf_counter())
                        yield _sse("tool", {"name": ev["name"]})
                    elif etype == "on_tool_end":
                        name, t = tool_starts.pop(ev["run_id"], (ev.get("name", "tool"), None))
                        if t is not None:
                            tracer.add(f"tool:{name}", int((time.perf_counter() - t) * 1000))
                    elif etype == "on_chat_model_stream":
                        text = ev["data"]["chunk"].content
                        if text:
                            full_answer += text
                            yield _sse("delta", {"content": text})

                sources = _dedupe_sources(sources_chunks)
                tracer.add(
                    "agent",
                    int((time.perf_counter() - agent_start) * 1000),
                    num_sources=len(sources),
                    answer_chars=len(full_answer),
                )
            else:
                ret_start = time.perf_counter()
                chunks = await hybrid_search(
                    search, openai_client, settings.azure_openai_embedding_deployment, req.question,
                    document_ids=doc_ids,
                    semantic_config=settings.azure_search_semantic_config or None,
                )
                tracer.add(
                    "retrieval",
                    int((time.perf_counter() - ret_start) * 1000),
                    num_chunks=len(chunks),
                )
                if not chunks:
                    sources = []
                    full_answer = NOT_FOUND_MESSAGE
                    yield _sse("delta", {"content": full_answer})
                else:
                    messages = build_messages(
                        req.question,
                        chunks,
                        history=history or None,
                        system_prompt=get_prompt(version),
                    )
                    gen_start = time.perf_counter()
                    stream = await openai_client.chat.completions.create(
                        model=settings.azure_openai_chat_deployment,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=2048,
                        stream=True,
                    )
                    full_answer = ""
                    async for event in stream:
                        if event.choices:
                            delta = event.choices[0].delta
                            if delta.content:
                                full_answer += delta.content
                                yield _sse("delta", {"content": delta.content})
                    tracer.add(
                        "generation",
                        int((time.perf_counter() - gen_start) * 1000),
                        answer_chars=len(full_answer),
                    )
                    sources = [Source(**c) for c in chunks]

            # ── Shared tail: emit sources, finish, persist ──
            sources_json = [s.model_dump(mode="json") for s in sources]
            yield _sse("sources", sources_json)

            latency_ms = int((time.perf_counter() - start) * 1000)
            yield _sse("done", {"latency_ms": latency_ms})

            db.add(
                Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=full_answer,
                    sources=sources_json,
                    latency_ms=latency_ms,
                )
            )
            db.add(
                QueryLog(
                    user_id=user_id,
                    question=req.question,
                    answer=full_answer,
                    sources=sources_json,
                    prompt_version=version,
                    latency_ms=latency_ms,
                )
            )
            db.add(tracer.to_model())
            await db.commit()

        except Exception as exc:
            logging.getLogger(__name__).exception("SSE stream failed")
            yield _sse("error", {"detail": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("", response_model=CursorPage[ConversationRead])
async def list_conversations(
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user),
) -> dict:
    q = select(Conversation)
    if user_id:
        q = q.where(Conversation.user_id == user_id)
    q = apply_cursor(q, cursor=cursor, sort_column=Conversation.updated_at, id_column=Conversation.id, limit=limit + 1)
    result = await db.execute(q)
    rows = list(result.scalars().all())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.updated_at, last.id)
    return {"items": rows, "next_cursor": next_cursor}


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user),
):
    conv = await db.get(
        Conversation, conversation_id, options=[selectinload(Conversation.messages)]
    )
    if not conv or not _own_conv(conv, user_id):
        raise HTTPException(status_code=404, detail="Konwersacja nie istnieje.")
    return conv


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user),
):
    conv = await db.get(Conversation, conversation_id)
    if not conv or not _own_conv(conv, user_id):
        raise HTTPException(status_code=404, detail="Konwersacja nie istnieje.")
    await db.delete(conv)
    await db.commit()
