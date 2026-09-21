import uuid
from datetime import date
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Event, Place
from schemas import (
    EventCreate,
    EventDetailRead,
    EventWithPlaceRead,
    PaginatedEventsPage,
    SeatsResponse,
)
from services.events_provider import EventsProviderClient, EventsProviderError
from services.seats_cache import seats_cache

router = APIRouter(prefix="/api/events", tags=["events"])


def _build_page_url(
    request: Request,
    page: int,
    page_size: int,
    date_from: date | None,
) -> str:
    base = str(request.base_url).rstrip("/") + request.url.path
    params: dict[str, str] = {"page": str(page), "page_size": str(page_size)}
    if date_from is not None:
        params["date_from"] = date_from.isoformat()
    return f"{base}?{urlencode(params)}"


@router.get("/", response_model=PaginatedEventsPage)
async def list_events(
    request: Request,
    date_from: date | None = Query(
        None, description="События с event_time >= указанной даты (YYYY-MM-DD)"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if date_from is not None:
        filters.append(Event.event_time >= date_from)

    count_stmt = select(func.count()).select_from(Event).where(*filters)
    total: int = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        select(Event)
        .options(selectinload(Event.place))
        .where(*filters)
        .order_by(Event.event_time.asc(), Event.id.asc())
        .limit(page_size)
        .offset(offset)
    )
    result = await db.execute(stmt)
    events = list(result.scalars().all())

    has_next = offset + len(events) < total
    has_previous = page > 1 and total > 0

    next_url = (
        _build_page_url(request, page + 1, page_size, date_from) if has_next else None
    )
    previous_url = (
        _build_page_url(request, page - 1, page_size, date_from)
        if has_previous
        else None
    )

    return PaginatedEventsPage(
        count=total,
        next=next_url,
        previous=previous_url,
        results=events,
    )


@router.get("/{event_id}", response_model=EventDetailRead)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Event).options(selectinload(Event.place)).where(Event.id == event_id)
    event = (await db.execute(stmt)).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


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
    return (await db.execute(stmt)).scalar_one()


@router.get("/{event_id}/seats/", response_model=SeatsResponse)
async def get_event_seats(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Seats are only available for published events "
                f"(current status: {event.status.value})"
            ),
        )

    async def _fetch() -> list[str]:
        async with EventsProviderClient() as client:
            return await client.fetch_seats(str(event_id))

    try:
        seats = await seats_cache.get_or_fetch(str(event_id), _fetch)
    except EventsProviderError as e:
        if e.status_code == 404:
            raise HTTPException(
                status_code=404, detail="Event not found in provider"
            ) from e
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Events Provider error: {e.detail}",
        ) from e

    return SeatsResponse(event_id=event_id, available_seats=seats)
