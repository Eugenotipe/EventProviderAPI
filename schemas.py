import re
import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class PlaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=500)
    seats_pattern: str = Field(..., min_length=1, max_length=1000)

    @field_validator("seats_pattern")
    @classmethod
    def validate_seats_pattern(cls, v):
        if not re.match(r"^[A-Z]+\d+-\d+(,[A-Z]+\d+-\d+)*$", v):
            raise ValueError('seats_pattern must match "A1-1000,B1-2000"')
        return v


class PlaceCreate(PlaceBase):
    pass


class PlaceRead(PlaceBase):
    id: uuid.UUID
    changed_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


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


class EventBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    event_time: datetime
    registration_deadline: datetime

    @model_validator(mode="after")
    def check_dates(self):
        if self.registration_deadline >= self.event_time:
            raise ValueError("registration_deadline must be before event_time")
        return self


class EventCreate(EventBase):
    place_id: uuid.UUID


class EventRead(EventBase):
    id: uuid.UUID
    status: str
    number_of_visitors: int
    place_id: uuid.UUID
    changed_at: datetime
    created_at: datetime
    status_changed_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EventWithPlaceRead(EventRead):
    place: PlaceRead


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


class PaginatedEvents(BaseModel):
    next: str | None
    previous: str | None
    results: list[EventWithPlaceRead]


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
