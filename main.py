import asyncio
import logging
import os
from contextlib import asynccontextmanager
from sqlalchemy import text

import uvicorn
from fastapi import FastAPI

from config import settings
from database import Base, engine
from routers import events, health, sync, tickets
from workers.sync_worker import sync_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'events'
                              AND column_name = 'numer_of_visitors'
                        ) THEN
                            ALTER TABLE events
                                RENAME COLUMN numer_of_visitors TO number_of_visitors;
                        END IF;
                    END $$;
                """))
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)

    task = asyncio.create_task(sync_loop())
    logger.info("Background sync worker started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Background sync worker stopped")

    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.include_router(health.router)
app.include_router(sync.router)
app.include_router(events.router)
app.include_router(tickets.router)


@app.get("/", tags=["root"])
async def read_root():
    return {"message": f"Hello from {settings.app_name}!"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8000)),
        reload=os.environ.get("RELOAD", "false").lower() == "true",
    )
