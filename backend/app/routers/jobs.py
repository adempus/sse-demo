"""Job REST + SSE endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.database import async_session_factory, get_session
from app.events import JobEvent, bus
from app.models import Job, JobCreate, JobRead, JobState, _utcnow
from app.worker import ensure_worker, is_running

router = APIRouter(prefix="/api", tags=["jobs"])


@router.post("/jobs", response_model=JobRead, status_code=201)
async def create_job(payload: JobCreate, session: AsyncSession = Depends(get_session)) -> Job:
    job = Job(name=payload.name.strip(), state=JobState.NOT_READY)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    assert job.id is not None
    # Announce the new job so every connected client adds it live...
    await bus.publish(JobEvent(job_id=job.id, name=job.name, state=job.state))
    # ...then run it server-side (independent of who is watching).
    await ensure_worker(job.id)
    return job


@router.get("/jobs", response_model=list[JobRead])
async def list_jobs(session: AsyncSession = Depends(get_session)) -> list[Job]:
    result = await session.execute(select(Job).order_by(desc(col(Job.created_at))))
    return list(result.scalars().all())


@router.get("/jobs/{job_id}", response_model=JobRead)
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/rerun", response_model=JobRead)
async def rerun_job(job_id: int, session: AsyncSession = Depends(get_session)) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if is_running(job_id):
        raise HTTPException(status_code=409, detail="Job is already running")
    job.state = JobState.NOT_READY
    job.updated_at = _utcnow()
    session.add(job)
    await session.commit()
    await session.refresh(job)
    # Broadcast the reset, then re-run server-side.
    await bus.publish(JobEvent(job_id=job_id, name=job.name, state=job.state))
    await ensure_worker(job_id)
    return job


@router.get("/events", response_class=EventSourceResponse)
async def stream_events() -> AsyncIterator[ServerSentEvent]:
    """Global firehose: every client streams all job state changes here.

    On connect we send a ``snapshot`` of all current jobs so the client is
    immediately in sync, then stream every subsequent state change to all
    connected clients (cross-device broadcast).

    FastAPI's ``EventSourceResponse`` handles keep-alive pings, ``Cache-Control``
    and ``X-Accel-Buffering`` headers, and client-disconnect cleanup for us.
    """
    # Subscribe *first* so any transition that lands while we build the snapshot
    # is queued (not lost); the client upserts by job_id so a value appearing in
    # both the snapshot and the stream is harmless.
    async with bus.subscribe() as queue:
        async with async_session_factory() as session:
            result = await session.execute(select(Job).order_by(desc(col(Job.created_at))))
            snapshot = [
                {"job_id": j.id, "name": j.name, "state": j.state.value}
                for j in result.scalars().all()
            ]
            print("Snapshot:", snapshot)
        yield ServerSentEvent(data=snapshot, event="snapshot")

        while True:
            event = await queue.get()
            print("Event:", event)
            yield ServerSentEvent(data=event.to_dict(), event="state")
