import base64
import json
import uuid
from datetime import UTC, datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Event, Place
from schemas import EventCreate, EventWithPlaceRead, PaginatedEvents

router = APIRouter(prefix="/api/events", tags=["events"])


def encode_cursor(changed_at, event_id):
    payload = {"changed_at": changed_at.isoformat(), "id": str(event_id)}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor):
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding)
        p = json.loads(raw)
        return datetime.fromisoformat(p["changed_at"]), uuid.UUID(p["id"])
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid cursor: {e}") from e


def build_url(request, changed_at, cursor):
    base = str(request.base_url).rstrip("/") + request.url.path
    params = {}
    if changed_at:
        params["changed_at"] = changed_at.isoformat()
    if cursor:
        params["cursor"] = cursor
    return f"{base}?{urlencode(params)}" if params else base


@router.get("/", response_model=PaginatedEvents)
async def list_events(
    request: Request,
    changed_at: datetime | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    if changed_at is not None and changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=UTC)

    stmt = select(Event).options(selectinload(Event.place))
    if changed_at is not None:
        stmt = stmt.where(Event.changed_at >= changed_at)
    if cursor is not None:
        cur_changed_at, cur_id = decode_cursor(cursor)
        stmt = stmt.where(
            tuple_(Event.changed_at, Event.id) < tuple_(cur_changed_at, cur_id)
        )

    stmt = stmt.order_by(Event.changed_at.desc(), Event.id.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    has_next = len(rows) > limit
    if has_next:
        rows = rows[:limit]

    next_url = None
    if has_next and rows:
        last = rows[-1]
        next_url = build_url(
            request, changed_at, encode_cursor(last.changed_at, last.id)
        )

    return PaginatedEvents(next=next_url, previous=None, results=rows)


@router.post(
    "/", response_model=EventWithPlaceRead, status_code=status.HTTP_201_CREATED
)
async def create_event(data: EventCreate, db: AsyncSession = Depends(get_db)):
    place = await db.get(Place, data.place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    event = Event(**data.model_dump())
    db.add(event)
    await db.commit()

    stmt = select(Event).options(selectinload(Event.place)).where(Event.id == event.id)
    result = await db.execute(stmt)
    return result.scalar_one()
