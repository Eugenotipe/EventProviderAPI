import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Event, Ticket
from schemas import TicketCreate, TicketCreated, TicketDeleted
from services.events_provider import EventsProviderClient, EventsProviderError
from services.seats_cache import seats_cache

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.post("", include_in_schema=False)
@router.post("/", response_model=TicketCreated, status_code=status.HTTP_201_CREATED)
async def create_ticket(data: TicketCreate, db: AsyncSession = Depends(get_db)):
    event = await db.get(Event, data.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Registration is not available (status: {event.status})",
        )

    from datetime import datetime, timezone

    if event.registration_deadline < datetime.now(tz=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration deadline has passed",
        )

    async with EventsProviderClient() as client:
        try:
            ticket_id = await client.register(
                event_id=str(data.event_id),
                first_name=data.first_name,
                last_name=data.last_name,
                seat=data.seat,
                email=data.email,
            )
        except EventsProviderError as e:
            raise HTTPException(
                status_code=e.status_code
                if e.status_code < 500
                else status.HTTP_502_BAD_GATEWAY,
                detail=f"Events Provider: {e.detail}",
            ) from e

    ticket_uuid = uuid.UUID(ticket_id) if isinstance(ticket_id, str) else ticket_id

    existing = await db.get(Ticket, ticket_uuid)
    if existing is not None:
        existing.event_id = data.event_id
        existing.first_name = data.first_name
        existing.last_name = data.last_name
        existing.email = data.email
        existing.seat = data.seat
    else:
        db.add(
            Ticket(
                id=ticket_uuid,
                event_id=data.event_id,
                first_name=data.first_name,
                last_name=data.last_name,
                email=data.email,
                seat=data.seat,
            )
        )
    await db.commit()

    seats_cache.invalidate(str(data.event_id))

    return TicketCreated(ticket_id=ticket_uuid)


@router.delete("/{ticket_id}", include_in_schema=False)
@router.delete("/{ticket_id}/", response_model=TicketDeleted)
async def delete_ticket(ticket_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    async with EventsProviderClient() as client:
        try:
            await client.unregister(
                event_id=str(ticket.event_id),
                ticket_id=str(ticket_id),
            )
        except EventsProviderError as e:
            if e.status_code != 404:
                raise HTTPException(
                    status_code=e.status_code
                    if e.status_code < 500
                    else status.HTTP_502_BAD_GATEWAY,
                    detail=f"Events Provider: {e.detail}",
                ) from e

    await db.delete(ticket)
    await db.commit()

    seats_cache.invalidate(str(ticket.event_id))

    return TicketDeleted(success=True)
