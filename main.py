import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from config import settings
from database import Base, engine
from routers import events, health, places


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(places.router)
app.include_router(events.router)
app.include_router(health.router)


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
