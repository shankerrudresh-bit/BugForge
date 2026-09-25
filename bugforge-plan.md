# BugForge — AI-Driven Chaos Engineering Platform

## Top-Level Overview

**Goal:** Build BugForge — a greenfield software platform that uses an LLM to automatically generate, review, execute, and report on multi-layered fault-injection (chaos engineering) scenarios against locally running Docker Compose environments.

**Core Problem Solved:** Human engineers only test simple, predictable failure scenarios. BugForge uses an LLM to generate multi-layered, compound failure scenarios (e.g. "database high latency + service memory spike during a rolling deployment") that humans rarely think to combine, then executes them safely and reports on system resilience.

**Scope (v1):**
- Python / FastAPI backend
- React or Next.js frontend
- PostgreSQL database (via SQLAlchemy + Alembic)
- LLM integration via IBM watsonx or OpenAI API
- Fault injection against Docker Compose services (network partition, process kill, CPU/memory limits)
- In-UI scenario review and approval before execution
- Post-run log collection, metrics capture, and pass/fail report per fault step

**Non-Goals (v1):**
- Kubernetes / cloud injection
- Multi-user auth / RBAC
- Distributed agent execution
- Real-time streaming dashboards (polling is sufficient)

---

## Architecture

### System Components

```
┌──────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)              │
│  - Architecture Input Form                           │
│  - Scenario Review & Approval UI                     │
│  - Run Status + Live Log Tail                        │
│  - Post-Run Report Viewer                            │
└──────────────────┬───────────────────────────────────┘
                   │ REST / JSON
┌──────────────────▼───────────────────────────────────┐
│                   BACKEND (FastAPI)                  │
│                                                      │
│  ┌─────────────────┐   ┌────────────────────────┐   │
│  │  Scenario API   │   │   Execution API        │   │
│  │  /scenarios     │   │   /runs                │   │
│  └────────┬────────┘   └───────────┬────────────┘   │
│           │                        │                 │
│  ┌────────▼────────┐   ┌───────────▼────────────┐   │
│  │  LLM Service    │   │  Fault Injection Engine │   │
│  │  (watsonx /     │   │  (Docker SDK + Chaos    │   │
│  │   OpenAI)       │   │   Toolkit adapters)     │   │
│  └─────────────────┘   └───────────┬────────────┘   │
│                                    │                 │
│                         ┌──────────▼─────────────┐  │
│                         │  Observability Collector│  │
│                         │  (log + metric capture) │  │
│                         └──────────┬─────────────┘  │
└────────────────────────────────────┼────────────────┘
                                     │
┌────────────────────────────────────▼────────────────┐
│              PostgreSQL Database                     │
│  - architectures, scenarios, runs, run_steps,        │
│    step_results, logs, metrics                       │
└──────────────────────────────────────────────────────┘
                   │ Docker SDK
┌──────────────────▼───────────────────────────────────┐
│          Target Environment (Docker Compose)         │
│  - User's locally running containers                 │
└──────────────────────────────────────────────────────┘
```

### Data Flow

1. User describes their system architecture in the UI (services, dependencies, SLOs).
2. Backend calls LLM with a structured prompt; LLM returns a JSON array of chaos scenarios.
3. Each scenario is a list of ordered fault steps (e.g. `[kill db, inject latency on api, spike memory on worker]`).
4. User reviews and approves/edits scenarios in the UI.
5. User triggers a run; Execution Engine applies each fault step sequentially or in parallel (as defined).
6. Observability Collector captures Docker container logs and `docker stats` metrics throughout the run.
7. After each step completes (or times out), the Engine evaluates health checks and marks the step pass/fail.
8. Final report is stored in PostgreSQL and rendered in the UI.

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffold & Repository Structure

**Intent:** Establish the full monorepo layout, dev tooling, and local-run configuration so every subsequent sub-task has a stable foundation to build on.

**Expected Outcomes:**
- `backend/` FastAPI app runs with `uvicorn` and returns a health-check response.
- `frontend/` Next.js app runs and displays a placeholder page.
- `docker-compose.dev.yml` starts both services plus a PostgreSQL instance.
- `.env.example` documents every required environment variable.
- `README.md` documents how to start the full stack locally.

**Todo List:**
1. Create `backend/` with `pyproject.toml` (or `requirements.txt`), `app/main.py` FastAPI entrypoint, and a `/health` route.
2. Create `frontend/` with `npx create-next-app` (TypeScript, Tailwind CSS).
3. Write `docker-compose.dev.yml` with services: `db` (postgres:16), `backend`, `frontend`.
4. Add Alembic to backend; create initial (empty) migration baseline.
5. Update `.env.example` with `DATABASE_URL`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `DOCKER_SOCKET_PATH`.
6. Write root `README.md` with `docker compose up` quickstart.

**Relevant Context:**
- Repo root: `c:\Users\rajku\OneDrive\Desktop\BugForge\BugForge`
- Security conventions: all secrets via `process.env` / `os.environ`, never hardcoded (see `SECURITY.MD`)

**Status:** [x] done

---

### Sub-Task 2 — Database Schema & Models

**Intent:** Define the PostgreSQL schema that persists every entity BugForge produces — architectures, generated scenarios, execution runs, per-step results, logs, and metrics.

**Expected Outcomes:**
- Alembic migration creates all tables cleanly on `alembic upgrade head`.
- SQLAlchemy ORM models exist for every table.
- Pydantic schemas (request/response) exist for each model.

**Todo List:**
1. Define SQLAlchemy models in `backend/app/models/`:
   - `Architecture` (id, name, description, services_json, created_at)
   - `Scenario` (id, architecture_id, title, description, steps_json, status[draft/approved/rejected], created_at)
   - `Run` (id, scenario_id, status[pending/running/completed/failed], started_at, finished_at)
   - `RunStep` (id, run_id, step_index, fault_type, target_service, parameters_json, status, started_at, finished_at)
   - `StepResult` (id, run_step_id, passed, health_check_output, notes)
   - `LogEntry` (id, run_id, run_step_id, container_name, timestamp, message)
   - `MetricSample` (id, run_id, run_step_id, container_name, cpu_pct, mem_mb, sampled_at)
2. Create Alembic migration for all tables.
3. Create Pydantic schemas in `backend/app/schemas/` mirroring each model.
4. Create `backend/app/db.py` with SQLAlchemy engine, session factory, and `get_db` dependency.

**Relevant Context:**
- `steps_json` stores the structured fault-step list generated by the LLM.
- `services_json` stores the user-described service graph (name, type, dependencies, SLOs).

**Status:** [x] done

---

### Sub-Task 3 — LLM Scenario Generation Service

**Intent:** Build the service that takes a structured architecture description and calls an LLM to produce a list of multi-layered chaos scenarios in a validated JSON schema.

**Expected Outcomes:**
- `POST /api/scenarios/generate` accepts an architecture ID and returns a list of draft `Scenario` objects.
- The LLM prompt enforces a strict JSON output schema (array of scenario objects, each with ordered fault steps).
- The service works with both IBM watsonx and OpenAI; provider is selected via `LLM_PROVIDER` env var.
- Invalid or malformed LLM responses are caught and returned as a structured error.

**Todo List:**
1. Create `backend/app/services/llm_service.py`:
   - `LLMProvider` enum (`watsonx`, `openai`).
   - `generate_scenarios(architecture: ArchitectureSchema) -> list[ScenarioSchema]` function.
   - Structured system prompt that enforces JSON output with the scenario schema.
   - Provider-specific client initialization (watsonx `ibm-generative-ai` SDK, or `openai` SDK).
   - JSON parse + Pydantic validation of LLM response; retry once on parse failure.
2. Create `backend/app/routers/scenarios.py`:
   - `POST /api/scenarios/generate` — calls `llm_service`, persists draft scenarios, returns list.
   - `GET /api/scenarios/{id}` — fetch single scenario.
   - `PATCH /api/scenarios/{id}/status` — approve / reject a scenario.
   - `GET /api/architectures/{arch_id}/scenarios` — list all scenarios for an architecture.
3. Create `backend/app/routers/architectures.py`:
   - `POST /api/architectures` — create architecture record.
   - `GET /api/architectures/{id}` — fetch architecture.

**Relevant Context:**
- IBM watsonx SDK: `ibm-generative-ai` (Python). Auth via `WATSONX_API_KEY` + `WATSONX_PROJECT_ID`.
- OpenAI SDK: `openai` (Python). Auth via `OPENAI_API_KEY`.
- The LLM prompt must include fault types available to the execution engine (see Sub-Task 4).

**Status:** [x] done

---

### Sub-Task 4 — Fault Injection Engine

**Intent:** Build the execution engine that translates a scenario's fault steps into real Docker operations, applies them sequentially/in parallel as defined, and records which step is active at each moment.

**Expected Outcomes:**
- `POST /api/runs` starts an async run for an approved scenario.
- `GET /api/runs/{id}` returns run status and all step statuses.
- The engine supports fault types: `kill_container`, `pause_container`, `network_partition`, `cpu_stress`, `memory_stress`, `inject_latency`.
- Each fault is applied and then automatically reversed after a configurable duration.
- Run state is persisted in PostgreSQL in real time (not only at end).

**Todo List:**
1. Create `backend/app/services/fault_engine.py`:
   - `FaultType` enum covering: `kill_container`, `pause_container`, `network_partition`, `cpu_stress`, `memory_stress`, `inject_latency`.
   - `apply_fault(step: RunStepSchema) -> None` — dispatches to the correct Docker SDK call.
   - `revert_fault(step: RunStepSchema) -> None` — reverses the fault (unpause, remove tc rule, etc.).
   - Uses `docker` Python SDK (`docker.from_env()`) to control containers.
   - Network partition uses `docker network disconnect` / `docker network connect`.
   - Latency injection uses `docker exec` to run `tc netem` inside target container (requires `iproute2`).
   - CPU/memory stress uses `docker update --cpus` / `--memory` (or `stress-ng` via `docker exec`).
2. Create `backend/app/services/run_executor.py`:
   - `execute_run(run_id: int, db: Session) -> None` — async coroutine (runs in `BackgroundTasks`).
   - Iterates ordered `RunStep` records; applies fault, waits `duration_seconds`, reverts fault.
   - Updates `Run.status` and `RunStep.status` in the DB after each step.
   - Catches exceptions per step; marks step failed but continues run (configurable).
3. Create `backend/app/routers/runs.py`:
   - `POST /api/runs` — creates `Run` + `RunStep` records, enqueues `execute_run` as a background task.
   - `GET /api/runs/{id}` — returns run with nested steps.
   - `GET /api/runs/{id}/steps` — list steps with status.

**Relevant Context:**
- Docker SDK: `docker` PyPI package.
- Background execution: FastAPI `BackgroundTasks` (sufficient for v1; no Celery needed).
- All container names come from `target_service` field in each step, matched to the Docker Compose service name.

**Status:** [x] done

---

### Sub-Task 5 — Observability Collector

**Intent:** During a run, continuously capture container logs and `docker stats` metrics, store them in PostgreSQL, and expose them via API so the UI can display live and historical data.

**Expected Outcomes:**
- Log entries are captured for all targeted containers during each step and stored in `LogEntry`.
- CPU % and memory MB samples are captured every ~2 seconds during each step and stored in `MetricSample`.
- `GET /api/runs/{id}/logs` and `GET /api/runs/{id}/metrics` endpoints return captured data.

**Todo List:**
1. Create `backend/app/services/observability.py`:
   - `collect_logs(container_name: str, run_id: int, step_id: int, db: Session, stop_event: asyncio.Event)` — streams Docker container logs via `container.logs(stream=True)` and writes `LogEntry` rows.
   - `collect_metrics(container_name: str, run_id: int, step_id: int, db: Session, stop_event: asyncio.Event)` — polls `container.stats(stream=True)` every 2 seconds and writes `MetricSample` rows.
   - Both run as concurrent `asyncio` tasks alongside the fault executor.
2. Integrate collection start/stop into `run_executor.py` (start collectors when step begins; stop when step ends).
3. Add routes to `runs.py`:
   - `GET /api/runs/{id}/logs?step_id=&container=` — paginated log entries.
   - `GET /api/runs/{id}/metrics?step_id=&container=` — metric samples.

**Relevant Context:**
- `container.logs(stream=True)` and `container.stats(stream=True)` are blocking generators — wrap in `asyncio.to_thread` or run in `ThreadPoolExecutor`.

**Status:** [x] done

---

### Sub-Task 6 — Post-Run Report Engine

**Intent:** After a run completes, compute a structured pass/fail report per fault step including a final system-resilience summary optionally narrated by the LLM.

**Expected Outcomes:**
- `GET /api/runs/{id}/report` returns a fully populated report object.
- Each step shows: fault applied, duration, pass/fail, health check output, key metrics (peak CPU, peak memory).
- An optional LLM-generated narrative summary is included if `LLM_REPORT_NARRATIVE=true`.

**Todo List:**
1. Create `backend/app/services/report_service.py`:
   - `build_report(run_id: int, db: Session) -> RunReportSchema` — aggregates `RunStep`, `StepResult`, `MetricSample`, and `LogEntry` into a structured report.
   - Computes per-step: peak CPU, peak memory, error log count, pass/fail.
   - Optionally calls LLM with aggregated metrics to generate a narrative resilience assessment.
2. Add `GET /api/runs/{id}/report` route to `runs.py`.
3. Define `RunReportSchema` Pydantic model with nested per-step summaries.

**Relevant Context:**
- Health check per step: presence of error-level log lines or step `status == failed` determines pass/fail.
- LLM narrative prompt: summarize the system's behavior under each fault and overall resilience score (1–10).

**Status:** [x] done

---

### Sub-Task 7 — Frontend: Architecture Input & Scenario Review

**Intent:** Build the two primary frontend flows — (1) describing a system architecture to seed LLM generation, and (2) reviewing, editing, and approving generated chaos scenarios before execution.

**Expected Outcomes:**
- User can fill out an Architecture form (service name, type, dependencies, SLOs) and submit.
- After submission, the UI calls the generate endpoint and displays a list of generated scenarios.
- Each scenario shows its fault steps in a readable timeline; user can approve or reject each scenario.

**Todo List:**
1. Set up Next.js API client in `frontend/lib/api.ts` wrapping all backend endpoints (typed with TypeScript interfaces matching backend Pydantic schemas).
2. Build `frontend/app/architectures/new/page.tsx` — architecture creation form (dynamic service rows).
3. Build `frontend/app/scenarios/page.tsx` — list of scenarios for a given architecture with Approve/Reject buttons.
4. Build `frontend/components/ScenarioCard.tsx` — renders scenario title, description, and ordered fault-step timeline.
5. Style with Tailwind CSS; use a minimal component library (shadcn/ui recommended for consistency).

**Relevant Context:**
- Fault step timeline should show: step index, fault type badge, target service, duration, and any parameters.
- Approval calls `PATCH /api/scenarios/{id}/status`.

**Status:** [x] done

---

### Sub-Task 8 — Frontend: Run Execution & Report Viewer

**Intent:** Build the execution trigger UI (launch a run from an approved scenario), a live run-status view with polling log/metric display, and the final post-run report view.

**Expected Outcomes:**
- User can start a run from the scenario detail page.
- Run status page polls `GET /api/runs/{id}` every 3 seconds and shows current step, step statuses, and a live log tail.
- After run completes, a report page renders the full pass/fail summary with metric charts per step.

**Todo List:**
1. Build `frontend/app/runs/[id]/page.tsx` — run status view with step progress timeline and log tail (polling via `setInterval`).
2. Build `frontend/app/runs/[id]/report/page.tsx` — post-run report with per-step pass/fail cards and metric charts.
3. Add a simple line chart component (`recharts` library) for CPU % and memory MB over time per step.
4. Add a "Launch Run" button to the scenario detail page (`/scenarios/[id]`) that calls `POST /api/runs`.
5. Show LLM narrative summary (if present) as a highlighted assessment card at the top of the report.

**Relevant Context:**
- Polling interval: 3 seconds on run status page; switch to non-polling once `Run.status == completed | failed`.
- Metric charts: one chart per targeted container, X-axis = time offset from step start, Y-axis = CPU % / memory MB.

**Status:** [x] done

---

### Sub-Task 9 — Integration, End-to-End Test & Documentation

**Intent:** Wire all layers together, verify the complete happy-path flow works end-to-end in a local Docker Compose environment, and document the system.

**Expected Outcomes:**
- A single `docker compose up` starts the full stack (db, backend, frontend, a sample target app).
- A documented walkthrough (README) can be followed to complete a full chaos run end-to-end.
- At minimum one automated integration test covers: create architecture → generate scenarios → approve → run → report.
- `ARCHITECTURE.md` documents component responsibilities, data flow, and environment variables.

**Todo List:**
1. Add a `sample-target/` directory with a simple 2-service Docker Compose app (e.g. FastAPI + PostgreSQL) that will be the fault-injection target.
2. Add `sample-target` service definitions to `docker-compose.dev.yml`.
3. Write `backend/tests/test_e2e.py` using `pytest` + `httpx` that covers the full flow against a live test DB.
4. Update `README.md` with full quickstart, env variable table, and walkthrough.
5. Write `ARCHITECTURE.md` with component diagram, data flow narrative, and extension guide.

**Relevant Context:**
- The `sample-target` must have `iproute2` installed in its image for `tc netem` latency injection to work.
- Use `pytest-asyncio` for async test support.

**Status:** [x] done

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `LLM_PROVIDER` | Yes | `watsonx` or `openai` |
| `LLM_API_KEY` | Yes | API key for the selected LLM provider |
| `LLM_MODEL` | Yes | Model ID (e.g. `ibm/granite-13b-chat-v2` or `gpt-4o`) |
| `WATSONX_PROJECT_ID` | If watsonx | IBM watsonx project ID |
| `DOCKER_SOCKET_PATH` | No | Defaults to `/var/run/docker.sock` |
| `LLM_REPORT_NARRATIVE` | No | `true` to enable LLM run narrative |

---

## Key Dependencies

### Backend (Python)
- `fastapi`, `uvicorn[standard]`
- `sqlalchemy`, `alembic`, `psycopg2-binary`
- `pydantic`, `pydantic-settings`
- `docker` (Docker SDK for Python)
- `ibm-generative-ai` (watsonx) or `openai`
- `pytest`, `httpx`, `pytest-asyncio`

### Frontend (Node.js)
- `next`, `react`, `typescript`
- `tailwindcss`
- `shadcn/ui`
- `recharts`
- `axios` or native `fetch`
