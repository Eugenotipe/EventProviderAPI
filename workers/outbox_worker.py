import asyncio
import logging

from services.outbox import process_batch

logger = logging.getLogger(__name__)

OUTBOX_INTERVAL_SECONDS = 5
OUTBOX_ERROR_SLEEP_SECONDS = 30


async def outbox_loop() -> None:
    logger.info("Outbox worker started")

    while True:
        try:
            processed = await process_batch()
            if processed == 0:
                await asyncio.sleep(OUTBOX_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("Outbox worker cancelled")
            raise
        except Exception:
            logger.exception(
                f"Outbox loop error, sleeping {OUTBOX_ERROR_SLEEP_SECONDS}s"
            )
            await asyncio.sleep(OUTBOX_ERROR_SLEEP_SECONDS)
