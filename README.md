# SSE State Demo

A small fullstack demo of **real-time communication with FastAPI Server-Sent
Events** driving a **React** frontend. Click a button, and a backend job walks
through five states — streamed to the browser live over SSE.

```
Not Ready → Queued → In Progress → Success (≈80%) | Failed (≈20%)
```

Waits between transitions are randomized to simulate real work.

## Architecture

```
┌──────────────┐   POST /api/jobs        ┌──────────────────────┐
│  Device A    │ ──────────────────────► │   FastAPI backend    │
│ (React SPA)  │   POST .../rerun         │                      │
│              │                          │  ┌────────────────┐  │
│              │   GET /api/events (SSE)  │  │ state machine  │  │
│              │ ◄════════ firehose ════  │  │    worker      │  │
└──────────────┘                          │  └───────┬────────┘  │
┌──────────────┐   GET /api/events (SSE)  │   global pub/sub bus │
│  Device B    │ ◄════════ firehose ════  │   (broadcast)        │
│ (phone/etc)  │                          │   SQLModel ─► SQLite │
└──────────────┘                          └──────────────────────┘
```

- **One global firehose.** Every device opens a single `EventSource` to
  `/api/events`. On connect the server sends a `snapshot` of all jobs, then
  streams every subsequent `state` change to **all** connected clients — so a
  job run on one device updates live on every other device (broadcast).
- **Actions are server-side.** `POST /api/jobs` and `POST /api/jobs/{id}/rerun`
  start the state-machine worker on the backend, independent of who's watching.
  The resulting transitions come back over the firehose.
- **Running is derived from state.** The UI treats `Queued`/`In Progress` as
  "running", so the Run button disables on every device, not just the one that
  clicked.
- The event bus is **in-process (asyncio)** — perfect for a single container.
  To scale to multiple workers/replicas, swap it for **Redis pub/sub** so events
  published on one process reach clients connected to another.
- SSE is served with FastAPI's **native `EventSourceResponse`** (`fastapi.sse`,
  added in 0.135.0): the path operation just `yield`s `ServerSentEvent`s, and
  FastAPI handles keep-alive pings, `Cache-Control`, `X-Accel-Buffering`, and
  client-disconnect cleanup.
- Job state is persisted with **SQLModel**; schema changes run via **Alembic**.

## Stack

| Layer     | Tech                                                          |
|-----------|--------------------------------------------------------------|
| Backend   | FastAPI · SQLModel · SSE · **uv** · **ruff** · **ty** · pytest |
| Frontend  | React 19 · TypeScript · Vite · **pnpm** · vitest · prettier  |
| Delivery  | Docker · docker compose · nginx (SSE-aware reverse proxy)     |

## Quick start (Docker)

```bash
make up
```

Then open **http://localhost:8080** and hit **Run Job**.

`make up` builds both images and starts the stack. nginx serves the built SPA
and reverse-proxies `/api` to the backend with buffering disabled (required for
SSE).

## Local development (no Docker)

```bash
make install        # uv sync + pnpm install
make dev-backend    # terminal 1 → http://localhost:8000
make dev-frontend   # terminal 2 → http://localhost:5173
```

The Vite dev server proxies `/api` to the backend on `:8000`.

## Quality gates

```bash
make lint        # ruff + eslint
make typecheck   # ty + tsc
make test        # pytest + vitest
make check       # all of the above
```

Run `make help` to see every target.

## Layout

```
sse-state-demo/
├── backend/            FastAPI + SQLModel service
│   ├── app/
│   │   ├── main.py         app factory, CORS, lifespan
│   │   ├── models.py       JobState enum + SQLModel table
│   │   ├── database.py     async engine / session
│   │   ├── events.py       in-process broadcast bus (JobEvent)
│   │   ├── worker.py       state-machine worker
│   │   ├── migrations/     Alembic migrations
│   │   └── routers/jobs.py REST + SSE firehose endpoints
│   └── tests/
├── frontend/           React + Vite SPA
│   └── src/
│       ├── api.ts             fetch helpers (create / rerun)
│       ├── useJobs.ts         single-firehose EventSource hook
│       ├── components/StateBadge.tsx
│       ├── components/JobRow.tsx
│       └── App.tsx
├── docker-compose.yml
└── Makefile
```
