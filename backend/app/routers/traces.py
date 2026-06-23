"""Read access to request traces (stage 3 observability viewer)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import auth_deps, get_current_user
from app.db.models import Trace
from app.db.session import get_db
from app.pagination import apply_cursor, encode_cursor
from app.schemas.pagination import CursorPage
from app.schemas.trace import TraceRead

router = APIRouter(prefix="/api/traces", tags=["traces"], dependencies=auth_deps())


@router.get("", response_model=CursorPage[TraceRead])
async def list_traces(
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user),
) -> dict:
    q = select(Trace)
    if user_id:
        q = q.where(Trace.user_id == user_id)
    q = apply_cursor(q, cursor=cursor, sort_column=Trace.created_at, id_column=Trace.id, limit=limit + 1)
    result = await db.execute(q)
    rows = list(result.scalars().all())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    return {"items": rows, "next_cursor": next_cursor}


@router.get("/{trace_id}", response_model=TraceRead)
async def get_trace(
    trace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user),
) -> Trace:
    trace = await db.get(Trace, trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    if user_id and trace.user_id and trace.user_id != user_id:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
