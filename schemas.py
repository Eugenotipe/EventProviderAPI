import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class PlaceShortRead(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    address: str
    model_config = ConfigDict(from_attributes=True)


class PlaceDetailRead(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    address: str
    seats_pattern: str
    model_config = ConfigDict(from_attributes=True)


class EventListItemRead(BaseModel):
    id: uuid.UUID
    name: str
    place: PlaceShortRead
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int
    model_config = ConfigDict(from_attributes=True)


class EventDetailRead(BaseModel):
    id: uuid.UUID
    name: str
    place: PlaceDetailRead
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int
    model_config = ConfigDict(from_attributes=True)


class SyncTriggerResponse(BaseModel):
    status: str
    message: str


class PaginatedEventsPage(BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[EventListItemRead]


class SeatsResponse(BaseModel):
    event_id: uuid.UUID
    available_seats: list[str]


class TicketCreate(BaseModel):
    event_id: uuid.UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    seat: str = Field(..., min_length=1, max_length=20)


class TicketCreated(BaseModel):
    ticket_id: uuid.UUID


class TicketDeleted(BaseModel):
    success: bool
