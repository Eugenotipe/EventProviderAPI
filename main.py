from contextlib import asynccontextmanager

import os
import uvicorn

from fastapi import FastAPI

from config import settings
from database import engine, Base
from routers import events


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.include_router(events.router)

@app.get("/", tags=["root"])
async def read_root():
    return {
        "message": f"Hello from {settings.app_name}!",
        "docs": "/docs",
        "redoc": "/redoc",
    }

@app.get("/api/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app",
                host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", 8080)),)