"""End-to-end tests: job lifecycle, listing, rerun, and the global SSE firehose.

Non-streaming endpoints are tested via httpx ASGITransport (fast, in-process).
The firehose is an *infinite* stream, which ASGITransport buffers rather than
streams — so those tests run against a real uvicorn server in a background
thread (also a more faithful test of the streaming path).
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from collections.abc import Iterator

import httpx
import pytest
import uvicorn
from app.events import EventBus, JobEvent
from app.main import app
from app.models import JobState
from asgi_lifespan import LifespanManager
from httpx import ASGITransport


@pytest.fixture
async def client():
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server() -> Iterator[str]:
    """Run the real app on a background uvicorn thread; yield its base URL."""
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{port}"
    # Wait for readiness.
    for _ in range(100):
        try:
            httpx.get(f"{base}/api/health", timeout=0.5)
            break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        raise RuntimeError("live server did not start")

    yield base

    server.should_exit = True
    thread.join(timeout=5)


# --------------------------------------------------------------------------- #
# Fast in-process tests (ASGITransport)
# --------------------------------------------------------------------------- #


async def test_health(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_create_job_requires_name(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/jobs", json={})
    assert resp.status_code == 422


async def test_create_job_starts_not_ready(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/jobs", json={"name": "Nightly export"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Nightly export"
    assert body["state"] == "Not Ready"
    assert isinstance(body["id"], int)


async def test_list_jobs(client: httpx.AsyncClient) -> None:
    await client.post("/api/jobs", json={"name": "Job A"})
    await client.post("/api/jobs", json={"name": "Job B"})
    resp = await client.get("/api/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) >= 2
    names = {j["name"] for j in jobs}
    assert {"Job A", "Job B"} <= names


async def test_event_bus_broadcasts_to_all_subscribers() -> None:
    """The bus fans one event out to every subscriber (broadcast semantics)."""
    fresh = EventBus()
    async with fresh.subscribe() as q1, fresh.subscribe() as q2:
        await fresh.publish(JobEvent(job_id=7, name="X", state=JobState.QUEUED))
        e1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
    assert e1 == e2
    assert e1.job_id == 7
    assert e1.state is JobState.QUEUED


# --------------------------------------------------------------------------- #
# Firehose tests (real server — infinite stream)
# --------------------------------------------------------------------------- #


def _collect_states_for(base: str, job_id: int, timeout: float = 30.0) -> list[str]:
    """Open the firehose and collect states for `job_id` until it terminates."""
    states: list[str] = []
    deadline = time.monotonic() + timeout
    with httpx.stream("GET", f"{base}/api/events", timeout=timeout) as resp:
        assert resp.status_code == 200
        event: str | None = None
        for line in resp.iter_lines():
            if line.startswith("event:"):
                event = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                payload = json.loads(line.removeprefix("data:").strip())
                if event == "snapshot":
                    for item in payload:
                        if item["job_id"] == job_id:
                            states.append(item["state"])
                elif event == "state" and payload["job_id"] == job_id:
                    states.append(payload["state"])
            if states and states[-1] in {"Success", "Failed"}:
                break
            if time.monotonic() > deadline:
                raise AssertionError("firehose did not reach terminal state in time")
    return states


def test_firehose_snapshot_includes_existing_jobs(live_server: str) -> None:
    job_id = httpx.post(f"{live_server}/api/jobs", json={"name": "Snapshot me"}).json()["id"]

    with httpx.stream("GET", f"{live_server}/api/events", timeout=10.0) as resp:
        assert resp.status_code == 200
        event: str | None = None
        for line in resp.iter_lines():
            if line.startswith("event:"):
                event = line.removeprefix("event:").strip()
            elif line.startswith("data:") and event == "snapshot":
                payload = json.loads(line.removeprefix("data:").strip())
                ids = {item["job_id"] for item in payload}
                assert job_id in ids
                return
    raise AssertionError("no snapshot received")


def test_firehose_broadcasts_state_changes(live_server: str) -> None:
    # Creating a job auto-runs it server-side; the firehose sees the transitions.
    job_id = httpx.post(f"{live_server}/api/jobs", json={"name": "Stream me"}).json()["id"]
    states = _collect_states_for(live_server, job_id)
    assert "Queued" in states
    assert "In Progress" in states
    assert states[-1] in {"Success", "Failed"}


def test_rerun_job(live_server: str) -> None:
    job_id = httpx.post(f"{live_server}/api/jobs", json={"name": "Rerun me"}).json()["id"]
    first = _collect_states_for(live_server, job_id)
    assert first[-1] in {"Success", "Failed"}

    rerun = httpx.post(f"{live_server}/api/jobs/{job_id}/rerun")
    assert rerun.status_code == 200
    assert rerun.json()["state"] == "Not Ready"

    second = _collect_states_for(live_server, job_id)
    assert second[-1] in {"Success", "Failed"}
