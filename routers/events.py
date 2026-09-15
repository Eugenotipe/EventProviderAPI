import base64
import json
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Event
from schemas import PaginatedEvents, EventWithPlaceRead

router = APIRouter(prefix="/api/events", tags=["events"])

def encode_cursor(changed_at: datetime, event_id: uuid.UUID) -> str:
    payload = {"changed_at": changed_at.isoformat(), "id": str(event_id)}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")

def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding)
        payload = json.loads(raw)
        return datetime.fromisoformat(payload["changed_at"]), uuid.UUID(payload["id"])
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid cursor: {e}")

def build_url(request: Request, changed_at: datetime | None, cursor: str | None) -> str:
    base = str(request.base_url).rstrip("/") + request.url.path
    params: dict[str, str] = {}
    if changed_at is not None:
        params["changed_at"] = changed_at.isoformat()
    if cursor is not None:
        params["cursor"] = cursor
    return f"{base}?{urlencode(params)}" if params else base


@router.get("/", response_model=PaginatedEvents)
async def list_events(
    request: Request,
    changed_at: datetime | None = Query(
        None, description="Вернуть события, изменённые в этот момент или позже"
    ),
    cursor: str | None = Query(None, description="Курсор для следующей страницы"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    if changed_at is not None and changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)

    stmt = select(Event).options(selectinload(Event.place))

    if changed_at is not None:
        stmt = stmt.where(Event.changed_at >= changed_at)

    if cursor is not None:
        cur_changed_at, cur_id = decode_cursor(cursor)
        stmt = stmt.where(
            tuple_(Event.changed_at, Event.id) < tuple_(cur_changed_at, cur_id)
        )

    stmt = (
        stmt.order_by(Event.changed_at.desc(), Event.id.desc())
        .limit(limit + 1)
    )

    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    has_next = len(rows) > limit
    if has_next:
        rows = rows[:limit]

    next_url = None
    if has_next and rows:
        last = rows[-1]
        next_url = build_url(request, changed_at, encode_cursor(last.changed_at, last.id))

    return PaginatedEvents(next=next_url, previous=None, results=rows)