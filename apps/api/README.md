# Lidl Tracker API

Read-only FastAPI service exposing ingested flyer data (Postgres via
`lidl_tracker.storage.database`) to the Next.js frontend in `apps/web`.

This is Phase 1 of `docs/backend-frontend-integration-plan.md`: flyer
list/detail only. Product endpoints and images land in later phases.

## Setup

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e "./ingestion[dev]"
.venv\Scripts\python -m pip install -e "./apps/api[dev]"
```

Both packages must be installed in the same environment — this package
imports `lidl_tracker.storage.database` directly rather than
reimplementing persistence.

## Run

```bash
docker compose up -d postgres
set DATABASE_URL=postgresql://lidl:lidl@localhost:5432/lidl_dev
.venv\Scripts\python -m lidl_tracker.cli_ingest --migrate
.venv\Scripts\python -m uvicorn api.main:app --reload --port 8000
```

Then browse the generated docs at http://localhost:8000/docs.

## Endpoints (Phase 1)

```
GET /health
GET /v1/flyers?year=&page=&page_size=
GET /v1/flyers/{slug}
```

See `docs/backend-frontend-integration-plan.md` §4 for the full API
design rationale and the endpoints planned for later phases.

## Tests

```bash
.venv\Scripts\python -m pytest apps/api/tests
```

All router tests mock `lidl_tracker.storage.database` — no live
database is required to run them.
