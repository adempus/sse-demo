"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import jobs


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    await init_db()
    yield


app = FastAPI(title="SSE State Demo", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
