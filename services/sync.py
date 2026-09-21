import asyncio
import logging
from datetime import date, datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from enums import SyncStatus
from models import Event, Place, SyncState
from services.events_provider import EventsProviderClient

logger = logging.getLogger(__name__)

FIRST_SYNC_DATE = date(2000, 1, 1)

_sync_lock = asyncio.Lock()


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


async def _get_or_create_state(db: AsyncSession) -> SyncState:
    state = await db.get(SyncState, 1)
    if state is None:
        state = SyncState(id=1, sync_status=SyncStatus.IDLE)
        db.add(state)
        await db.commit()
        await db.refresh(state)
    return state


async def _upsert_places(db: AsyncSession, events: list[dict]) -> None:
    seen: dict[str, dict] = {}
    for e in events:
        p = e["place"]
        seen[p["id"]] = p
    if not seen:
        return

    stmt = pg_insert(Place).values(
        [
            {
                "id": p["id"],
                "name": p["name"],
                "city": p["city"],
                "address": p["address"],
                "seats_pattern": p["seats_pattern"],
                "changed_at": _parse_dt(p["changed_at"]),
                "created_at": _parse_dt(p["created_at"]),
            }
            for p in seen.values()
        ]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "name": stmt.excluded.name,
            "city": stmt.excluded.city,
            "address": stmt.excluded.address,
            "seats_pattern": stmt.excluded.seats_pattern,
            "changed_at": stmt.excluded.changed_at,
        },
    )
    await db.execute(stmt)


async def _upsert_events(db: AsyncSession, events: list[dict]) -> None:
    if not events:
        return

    stmt = pg_insert(Event).values(
        [
            {
                "id": e["id"],
                "name": e["name"],
                "place_id": e["place"]["id"],
                "event_time": _parse_dt(e["event_time"]),
                "registration_deadline": _parse_dt(e["registration_deadline"]),
                "status": e["status"],
                "number_of_visitors": e["number_of_visitors"],
                "changed_at": _parse_dt(e["changed_at"]),
                "created_at": _parse_dt(e["created_at"]),
                "status_changed_at": _parse_dt(e["status_changed_at"]),
            }
            for e in events
        ]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "name": stmt.excluded.name,
            "place_id": stmt.excluded.place_id,
            "event_time": stmt.excluded.event_time,
            "registration_deadline": stmt.excluded.registration_deadline,
            "status": stmt.excluded.status,
            "number_of_visitors": stmt.excluded.number_of_visitors,
            "changed_at": stmt.excluded.changed_at,
            "status_changed_at": stmt.excluded.status_changed_at,
        },
    )
    await db.execute(stmt)


async def _do_sync() -> dict:
    async with AsyncSessionLocal() as db:
        state = await _get_or_create_state(db)

        state.sync_status = SyncStatus.RUNNING
        state.last_sync_time = datetime.now(tz=timezone.utc)
        state.last_error = None
        await db.commit()

        try:
            changed_at = (
                state.last_changed_at.date()
                if state.last_changed_at
                else FIRST_SYNC_DATE
            )
            logger.info(f"Sync start, changed_at={changed_at}")

            async with EventsProviderClient() as client:
                events = await client.fetch_events(changed_at)

            logger.info(f"Fetched {len(events)} events")

            await _upsert_places(db, events)
            await _upsert_events(db, events)

            if events:
                max_changed = max(_parse_dt(e["changed_at"]) for e in events)
                state.last_changed_at = max_changed

            state.sync_status = SyncStatus.SUCCESS
            await db.commit()

            logger.info(f"Sync success: {len(events)} events")
            return {"status": "success", "events_synced": len(events)}

        except Exception as e:
            await db.rollback()
            state = await db.get(SyncState, 1)
            if state is not None:
                state.sync_status = SyncStatus.FAILED
                state.last_error = str(e)[:1000]
                await db.commit()
            logger.exception("Sync failed")
            raise


async def run_sync() -> dict:
    async with _sync_lock:
        return await _do_sync()


def is_sync_running() -> bool:
    return _sync_lock.locked()
