"""Domain models and the job state enum."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class JobState(StrEnum):
    """The five states a job moves through."""

    NOT_READY = "Not Ready"
    QUEUED = "Queued"
    IN_PROGRESS = "In Progress"
    FAILED = "Failed"
    SUCCESS = "Success"


# Terminal states no worker should transition out of.
TERMINAL_STATES: frozenset[JobState] = frozenset({JobState.FAILED, JobState.SUCCESS})


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Job(SQLModel, table=True):
    """A unit of work whose lifecycle is streamed to clients."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    state: JobState = Field(default=JobState.NOT_READY)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class JobCreate(SQLModel):
    """Payload for creating a job."""

    name: str = Field(min_length=1, max_length=120)


class JobRead(SQLModel):
    """Serialized job returned to clients."""

    id: int
    name: str
    state: JobState
    created_at: datetime
    updated_at: datetime
