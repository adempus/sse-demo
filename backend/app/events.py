"""In-process async pub/sub bus broadcasting job state changes to all clients.

A single global stream: every published :class:`JobEvent` fans out to every live
subscriber, regardless of which job it belongs to. This is what powers the
cross-device "firehose" — one connection per client sees all job activity.

Good enough for a single-process demo. To scale across multiple workers or
replicas, swap this for Redis pub/sub (subscribers read from Redis instead of an
in-process queue) so events published on one process reach clients on another.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from app.models import JobState


@dataclass(frozen=True, slots=True)
class JobEvent:
    """A single job state change broadcast to all subscribers."""

    job_id: int
    name: str
    state: JobState

    def to_dict(self) -> dict[str, object]:
        return {"job_id": self.job_id, "name": self.name, "state": self.state.value}


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[JobEvent]] = set()
        self._lock = asyncio.Lock()

    async def publish(self, event: JobEvent) -> None:
        async with self._lock:
            queues = list(self._subscribers)
        for queue in queues:
            await queue.put(event)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[JobEvent]]:
        """Register a subscriber queue for the life of the context.

        Returns the raw queue so callers can ``await queue.get()`` directly —
        this is safe to wrap in ``asyncio.wait_for`` for heartbeats, unlike
        cancelling ``__anext__`` on an async generator (which corrupts it).
        """
        queue: asyncio.Queue[JobEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        try:
            yield queue
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    async def subscriber_count(self) -> int:
        async with self._lock:
            return len(self._subscribers)


bus = EventBus()
