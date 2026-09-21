import asyncio
import logging

from services.sync import run_sync

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 24 * 60 * 60
RETRY_ON_ERROR_SECONDS = 5 * 60


async def sync_loop() -> None:
    while True:
        try:
            result = await run_sync()
            logger.info(f"Periodic sync result: {result}")
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("Sync worker cancelled")
            raise
        except Exception:
            logger.exception("Periodic sync failed, retry in 5 min")
            await asyncio.sleep(RETRY_ON_ERROR_SECONDS)
