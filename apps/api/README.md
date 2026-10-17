# Lidl Tracker API

Read-only FastAPI service exposing ingested flyer data (Postgres via
`lidl_tracker.storage.database`) to the Next.js frontend in `apps/web`.

This implements the flyer list/detail routes, the Phase 3 flyer-card API, and
the provisional derived listing at `GET /v1/products` from
`docs/backend-frontend-integration-plan.md`. It does not expose canonical
product identities or product image URLs.
Render deployment settings are documented in
`docs/render-deployment.md`. The current deployment is the `main` branch
served by the `lidl-tracker-api` Render service.

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

For a production-style local launch, set `PORT` if needed and run:

```bash
python -m api.run
```

## Endpoints

```
GET /health
GET /v1/flyers?year=&page=&page_size=
GET /v1/flyers/{slug}
GET /v1/flyers/{slug}/products?page=&page_size=
GET /v1/products?page=&page_size=
```

The flyer products endpoint returns a paginated `{items, total, page,
page_size}` envelope of cards from the currently deployed parser version.
It retains `ok`, `partial`, and `failed` extraction statuses; card fields and
nullable values are documented by the generated OpenAPI schema. Pagination
defaults to 20 cards and accepts a maximum page size of 100. A known flyer
with no cards returns an empty page; an unknown slug returns 404.

The products endpoint returns a paginated `{items, total, page, page_size}`
catalogue derived from card observations on the active parser version. It
groups only observations with matching normalized brand/name, matching
description when present, and an exact positive structured quantity; cards
without enough identity data remain separate `observation_only` entries.
Each result has an opaque provisional
`derived_id`, not a canonical product ID or route slug, and retains the source
card observations and extraction statuses. Product category and image URL
are currently null. Last-seen is based only on valid ISO flyer start dates.
Pagination defaults to 20 derived results and accepts a maximum page size of
100; invalid parameters return 422. The endpoint does not add or alter schema.

See `docs/backend-frontend-integration-plan.md` for the response contract and
design rationale.

## Tests

```bash
.venv\Scripts\python -m pytest apps/api/tests
```

All router tests mock `lidl_tracker.storage.database` — no live
database is required to run them.
