"""Cursor-based pagination helpers.

Cursor format: base64(json({"ts": "<ISO timestamp>", "id": "<uuid>"}))
Stable ordering: (sort_column DESC, id DESC) — no rows skipped on timestamp collision.
"""

import base64
import json
import uuid
from datetime import datetime

from sqlalchemy import Select, and_, bindparam, or_
from sqlalchemy.types import DateTime


def encode_cursor(ts: datetime, row_id: uuid.UUID) -> str:
    payload = json.dumps({"ts": ts.isoformat(), "id": str(row_id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor))
        ts = datetime.fromisoformat(payload["ts"])
        return ts, uuid.UUID(payload["id"])
    except Exception:
        raise ValueError("Invalid cursor") from None


def apply_cursor(
    query: Select,
    *,
    cursor: str | None,
    sort_column,
    id_column,
    limit: int,
) -> Select:
    """Apply cursor filter + limit to a SELECT ordered by (sort_column DESC, id DESC)."""
    query = query.order_by(sort_column.desc(), id_column.desc())

    if cursor:
        ts, rid = decode_cursor(cursor)
        # Bind the full-precision, tz-aware datetime so the comparison stays
        # timestamptz ↔ timestamptz. The old code stringified to second
        # precision, which silently dropped every row sharing the cursor's
        # second (sort_column was neither < nor == the truncated value).
        ts_param = bindparam("cursor_ts", value=ts, type_=DateTime(timezone=True))
        query = query.where(
            or_(
                sort_column < ts_param,
                and_(sort_column == ts_param, id_column < rid),
            )
        )

    return query.limit(limit)
