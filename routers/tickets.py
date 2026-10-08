import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Event, IdempotencyKey, Outbox, Ticket
from schemas import TicketCreate, TicketCreated, TicketDeleted
from services.events_provider import EventsProviderClient, EventsProviderError
from services.idempotency import hash_request
from services.seats_cache import seats_cache

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.post("", include_in_schema=False, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TicketCreated, status_code=status.HTTP_201_CREATED)
async def create_ticket(data: TicketCreate, db: AsyncSession = Depends(get_db)):
    # ===================== Проверка идемпотентности =====================
    current_hash: str | None = None
    if data.idempotency_key:
        current_hash = hash_request(data)
        existing = await db.get(IdempotencyKey, data.idempotency_key)
        if existing is not None:
            if existing.request_hash != current_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key reused with different request data",
                )
            return TicketCreated(ticket_id=existing.ticket_id)

    # ===================== Обычные проверки события =====================
    event = await db.get(Event, data.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Registration is not available (status: {event.status})",
        )

    if event.registration_deadline < datetime.now(tz=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration deadline has passed",
        )

    # ===================== Внешний вызов до транзакции =====================
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

    # ===================== Одна транзакция: ticket + outbox + idempotency_key =====================
    try:
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

        message = f"Вы успешно зарегестрированы на мероприятие - {event.name}. Место: {data.seat}"
        outbox_entry = Outbox(
            event_type="ticket_created",
            payload={
                "message": message,
                "reference_id": str(ticket_uuid),
                "idempotency_key": f"ticket-{ticket_uuid}",
            },
            status="pending",
        )
        db.add(outbox_entry)

        if data.idempotency_key and current_hash is not None:
            db.add(
                IdempotencyKey(
                    key=data.idempotency_key,
                    request_hash=current_hash,
                    ticket_id=ticket_uuid,
                )
            )

        await db.commit()

    except IntegrityError:
        await db.rollback()

        existing = await db.get(IdempotencyKey, data.idempotency_key)
        if existing is None:
            raise

        if existing.request_hash != current_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key reused with different request data",
            ) from None

        return TicketCreated(ticket_id=existing.ticket_id)

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
