import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import Outbox
from services.capashino import CapashinoClient, CapashinoError

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
MAX_ATTEMPTS = 10


async def _process_one(db: AsyncSession, entry: Outbox):
    payload = entry.payload

    try:
        async with CapashinoClient() as client:
            await client.send_notification(
                message=payload["message"],
                reference_id=payload["reference_id"],
                idempotency_key=payload["idempotency_key"],
            )
        entry.status = "sent"
        entry.sent_at = datetime.now(tz=timezone.utc)
        logger.info(f"Outbox {entry.id} sent (attempts={entry.attempts + 1})")
    except CapashinoError as e:
        entry.attempts += 1
        entry.last_error = f"[{e.status_code}] {e.details}"[:1000]
        logger.warning(
            f"Outbox {entry.id} failed (attempt {entry.attempts}, "
            f"status={e.status_code}): {e.details}"
        )
    except Exception as e:
        entry.attempts += 1
        entry.last_error = str(e)[:1000]
        logger.exception(f"Outbox {entry.id} unexpected error")


async def process_batch(batch_size: int = BATCH_SIZE) -> int:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Outbox)
            .where(Outbox.status == "pending")
            .where(Outbox.attempts < MAX_ATTEMPTS)
            .order_by(Outbox.created_at.asc())
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )
        rows = list((await db.execute(stmt)).scalars().all())

        if not rows:
            return 0

        logger.info(f"Processing {len(rows)} outbox entries")

        for entry in rows:
            await _process_one(db, entry)

        await db.commit()

    return len(rows)
