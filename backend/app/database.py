"""Async SQLModel engine + session plumbing."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./jobs.db")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _run_upgrade() -> None:
    """Apply Alembic migrations up to head (sync — runs inside run_sync)."""
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")


async def init_db() -> None:
    """Bring the schema to head via Alembic migrations on startup.

    Runs in a worker thread so Alembic's env.py can spin up its own event loop
    (via ``asyncio.run``) without clashing with the running app loop.
    """
    await asyncio.to_thread(_run_upgrade)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding an async session."""
    async with async_session_factory() as session:
        yield session
