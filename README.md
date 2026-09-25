# BugForge

**AI-driven chaos engineering platform.** BugForge uses a large language model to generate multi-layered, compound fault-injection scenarios that human engineers rarely think to combine — then executes them against your live Docker Compose environment and produces a structured resilience report.

---

## What It Does

1. **Describe** your system architecture (services, types, dependencies, SLOs)
2. **AI generates** multi-layered chaos scenarios (e.g. "kill DB + inject latency on API + memory spike on worker — all at once")
3. **Review and approve** scenarios in the UI before any fault is injected
4. **Execute** — faults are injected into real Docker containers, then automatically reverted
5. **Report** — per-step pass/fail, peak CPU/memory charts, optional LLM narrative

---

## Quickstart

### Prerequisites
- Docker Desktop (with Docker Compose V2)
- An OpenAI API key **or** IBM watsonx credentials

### 1. Clone & configure

```bash
git clone <repo-url>
cd BugForge
cp .env.example .env
# Edit .env and fill in your API key
```

### 2. Start the full stack

```bash
docker compose -f docker-compose.dev.yml up --build
```

This starts:
| Service | URL |
|---|---|
| Frontend (Next.js) | http://localhost:3000 |
| Backend (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Sample target API | http://localhost:8080 |
| Sample target DB | localhost:5433 |

### 3. Run a chaos experiment

1. Open http://localhost:3000
2. Click **New Architecture** — describe your system
3. BugForge calls the LLM and shows generated scenarios
4. **Approve** the scenarios you want to test
5. Click **▶ Launch Run**
6. Watch the live step timeline and log tail
7. View the final **Report** with per-step pass/fail and metric charts

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `LLM_PROVIDER` | Yes | `openai` or `watsonx` |
| `LLM_API_KEY` | Yes | API key for the LLM provider |
| `LLM_MODEL` | Yes | Model ID (e.g. `gpt-4o` or `ibm/granite-13b-chat-v2`) |
| `WATSONX_PROJECT_ID` | If watsonx | IBM watsonx project ID |
| `WATSONX_API_URL` | If watsonx | watsonx endpoint (default: us-south) |
| `DOCKER_SOCKET_PATH` | No | Docker socket path (default: `/var/run/docker.sock`) |
| `LLM_REPORT_NARRATIVE` | No | `true` to add LLM-generated narrative to reports |

---

## Fault Types

| Fault | Description | Revert |
|---|---|---|
| `kill_container` | Terminates the container | Restarts it |
| `pause_container` | Freezes all container processes (SIGSTOP) | Unpauses |
| `network_partition` | Disconnects container from Docker network | Reconnects |
| `cpu_stress` | Pins CPU via `stress-ng` | Kills stress-ng |
| `memory_stress` | Allocates memory via `stress-ng` | Kills stress-ng |
| `inject_latency` | Adds network latency via `tc netem` | Removes tc rule |

> **Note:** `inject_latency` and `cpu/memory_stress` require `iproute2` and `stress-ng` in the target container. The sample target image includes both.

---

## Development

### Backend only

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend only

```bash
cd frontend
npm install
npm run dev
```

### Running tests

```bash
cd backend
TEST_API_URL=http://localhost:8000 pytest tests/test_e2e.py -v
```

---

## Project Structure

```
BugForge/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entrypoint
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── db.py                # SQLAlchemy engine + session
│   │   ├── models/              # ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routers/             # API route handlers
│   │   └── services/            # Business logic
│   │       ├── llm_service.py   # LLM scenario generation
│   │       ├── fault_engine.py  # Docker fault apply/revert
│   │       ├── run_executor.py  # Async run orchestrator
│   │       ├── observability.py # Log + metric collector
│   │       └── report_service.py# Post-run report builder
│   ├── alembic/                 # DB migrations
│   └── tests/
│       └── test_e2e.py
├── frontend/
│   └── src/
│       ├── app/                 # Next.js App Router pages
│       ├── components/          # Shared React components
│       └── lib/
│           └── api.ts           # Typed backend API client
├── sample-target/               # Fault-injection target app
├── docker-compose.dev.yml
└── ARCHITECTURE.md
```
