import uuid
import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from enums import EventStatus

class PlaceBase(BaseModel):
    name: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    seats_pattern: str = Field(..., min_length=1)

    @field_validator('seats_pattern')
    @classmethod
    def seats_pattern_validator(cls, v:str) -> str:
        pattern = re.compile('^[A-Z]+\d+-\d+(,[A-Z]+\d+-\d+)*$')
        if not pattern.match(v):
            raise ValueError(f'seats_pattern must match format "A1-1000,B1-2000"')
        return v

class PlaceCreate(BaseModel):
    pass

class PlaceRead(BaseModel):
    id: uuid.UUID
    changed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EventBase(BaseModel):
    name: str = Field(..., min_length=1)
    event_time: datetime
    registration_deadline: datetime

    @model_validator(mode="after")
    def check_dates(self):
        if self.registration_deadline >= self.event_time:
            raise ValueError('event_time must be after registration_deadline')
        return self

class EventCreate(EventBase):
    place_id: uuid.UUID

class EventsRead(BaseModel):
    id: uuid.UUID
    status: EventStatus
    number_of_visitors: int
    place_id: uuid.UUID
    changed_at: datetime
    created_at: datetime
    status_changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventWithPlaceRead(EventsRead):
    place: PlaceRead

class PaginatedEvents(BaseModel):
    next: str | None
    previous: str | None
    results: list[EventWithPlaceRead]