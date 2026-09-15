from sqlalchemy import select
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from models import Event, Place
from schemas import EventsList

async def get_events(db:AsyncSession, changed_at: DateTime) -> EventsList:
