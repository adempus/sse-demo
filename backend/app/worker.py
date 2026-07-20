"""The job state-machine worker.

Drives a job through Not Ready -> Queued -> In Progress -> Success|Failed,
persisting each transition and publishing it on the global event bus. Waits
between transitions are randomized to simulate real work.

Workers are triggered by the create/rerun actions (server-side), not by anyone
watching, and are de-duplicated so a job only ever has one worker running at a
time regardless of how many clients are connected.
"""

from __future__ import annotations

import asyncio
import random

from app.database import async_session_factory
from app.events import JobEvent, bus
from app.models import Job, JobState, _utcnow

# Probability the terminal state is Success rather than Failed.
SUCCESS_PROBABILITY = 0.8

# (min, max) seconds to wait before entering each state.
_TRANSITION_DELAYS: dict[JobState, tuple[float, float]] = {
    JobState.QUEUED: (0.5, 1.5),
    JobState.IN_PROGRESS: (1.0, 2.5),
}
_TERMINAL_DELAY = (1.5, 3.5)

# Track running workers so we never start two for the same job.
_running: set[int] = set()
_running_lock = asyncio.Lock()


async def _set_state(job_id: int, state: JobState) -> None:
    async with async_session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return
        job.state = state
        job.updated_at = _utcnow()
        session.add(job)
        await session.commit()
        name = job.name
    await bus.publish(JobEvent(job_id=job_id, name=name, state=state))


async def _run(job_id: int) -> None:
    try:
        for state in (JobState.QUEUED, JobState.IN_PROGRESS):
            lo, hi = _TRANSITION_DELAYS[state]
            await asyncio.sleep(random.uniform(lo, hi))
            await _set_state(job_id, state)

        await asyncio.sleep(random.uniform(*_TERMINAL_DELAY))
        terminal = JobState.SUCCESS if random.random() < SUCCESS_PROBABILITY else JobState.FAILED
        await _set_state(job_id, terminal)
    finally:
        async with _running_lock:
            _running.discard(job_id)


async def ensure_worker(job_id: int) -> bool:
    """Start the worker for a job exactly once.

    Returns True if a worker was started, False if one was already running.
    """
    async with _running_lock:
        if job_id in _running:
            return False
        _running.add(job_id)
    asyncio.create_task(_run(job_id))
    return True


def is_running(job_id: int) -> bool:
    """Whether a worker is currently active for this job."""
    return job_id in _running
