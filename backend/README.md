# SSE State Demo — Backend

FastAPI + SQLModel service that drives a job through five states and streams
transitions over Server-Sent Events.

## States

`Not Ready → Queued → In Progress → (Success | Failed)`

Success ~80% of the time. Waits between transitions are randomized.

## Run (standalone dev)

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Endpoints

| Method | Path                     | Description                                    |
|--------|--------------------------|------------------------------------------------|
| POST   | `/api/jobs`              | Create a job (starts in `Not Ready`) and run it |
| GET    | `/api/jobs`              | List all jobs (newest first)                   |
| GET    | `/api/jobs/{id}`         | Fetch current job state                        |
| POST   | `/api/jobs/{id}/rerun`   | Reset a job to `Not Ready` and run it again    |
| GET    | `/api/events`            | Global SSE firehose (snapshot + live updates)  |
| GET    | `/api/health`            | Liveness probe                                 |

Creating or re-running a job starts the state-machine worker server-side,
independent of who's watching. Every client subscribes to the single
`/api/events` firehose: on connect it receives a `snapshot` of all jobs, then
every subsequent `state` change — so activity on one device is broadcast to all.

SSE is served with FastAPI's native `EventSourceResponse` (`fastapi.sse`,
requires FastAPI ≥ 0.135.0), which supplies keep-alive pings, `Cache-Control`,
`X-Accel-Buffering`, and client-disconnect cleanup automatically.

## Tooling

- `uv run ruff check .` — lint
- `uv run ruff format .` — format
- `uv run ty check` — type check
- `uv run pytest` — tests
