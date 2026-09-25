# Lidl Spain flyer product tracker

Milestones 1–5 of the incremental plan: flyer acquisition, PDF inspection,
product-card grouping, deterministic field extraction and measurement.

**No OCR, no object detection, no LLM, no embeddings.** They were not
needed — see `docs/pdf-structure.md` for why.

## Setup

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e "./ingestion[dev]"
```

A read-only HTTP API for the Next.js frontend lives in `apps/api` — see
`apps/api/README.md` and `docs/backend-frontend-integration-plan.md`.

## Usage

```bash
# Milestone 1 — discover flyers and download PDFs (idempotent)
python -m lidl_tracker.cli_acquire --list
python -m lidl_tracker.cli_acquire --download-all
python -m lidl_tracker.cli_ingest --slug folleto-alimentacion-17-8-17-8-26-23-8-26-a07bd0
python -m lidl_tracker.cli_ingest --slug folleto-alimentacion-17-8-17-8-26-23-8-26-a07bd0,folleto-bazar-17-8-17-8-26-23-8-26-e0c443
# Validate R2 snapshots/PDFs, then rebuild flyer and product-card rows:
python -m lidl_tracker.cli_snapshot --dry-run
python -m lidl_tracker.cli_snapshot
python -m lidl_tracker.cli_restore --dry-run
python -m lidl_tracker.cli_restore --migrate
# GitHub Actions: run the "Lidl Flyer Ingest" workflow manually and enter
# one slug, or comma-separated slugs, in its optional "slug" input.

# Milestone 2 — inspect PDF structure
python -m lidl_tracker.cli_inspect data/raw/<flyer>.pdf --summary
python -m lidl_tracker.cli_inspect data/raw/<flyer>.pdf --page 13 --fonts

# Milestones 3-5 — extract products and measure quality
python -m lidl_tracker.cli_extract data/raw/<flyer>.pdf
python -m lidl_tracker.cli_extract data/raw/<flyer>.pdf --page 13 --show
python -m lidl_tracker.cli_extract data/raw/<flyer>.pdf --failures
python -m lidl_tracker.cli_extract data/raw/<flyer>.pdf --json data/out/f.json

pytest ingestion/tests
```

## Local development services

The production integrations can be exercised locally without touching the
production database, R2 bucket, or email account. Docker Compose provides
PostgreSQL, an S3-compatible MinIO bucket, and a Mailpit SMTP inbox.

```bash
cp .env.example .env.local
docker compose up -d
set -a && . ./.env.local && set +a
python -m lidl_tracker.cli_ingest --migrate --slug <slug>
python -m lidl_tracker.cli_watch --query "queso en salmuera" --to test@example.com
pytest ingestion/tests
```

The MinIO console is available at http://localhost:9001 (credentials
`minio` / `minio-password`) and the Mailpit inbox at http://localhost:8025.
Use `docker compose down -v` to discard the local database and bucket.

## Results on real flyers (2026-08-12)

| flyer             | pages | cards | ok  | partial | failed | name | price | quantity | unit price |
| ----------------- | ----- | ----- | --- | ------- | ------ | ---- | ----- | -------- | ---------- |
| ALIMENTACIÓN 10/8 | 67    | 245   | 243 | 2       | 0      | 100% | 100%  | 95.5%    | 88.6%      |
| ALIMENTACIÓN 17/8 | 51    | 186   | 182 | 4       | 0      | 100% | 100%  | 93.5%    | 89.8%      |
| BAZAR 10/8        | 23    | 69    | 69  | 0       | 0      | 100% | 100%  | 11.6%\*  | 0%\*       |
| BAZAR 17/8        | 31    | 135   | 135 | 0       | 0      | 100% | 100%  | 5.9%\*   | 1.5%\*     |

\* Non-food products genuinely have no weight or unit price.

**635 cards, 0 failures, 100% name + price coverage.**

## Layout

```
apps/                  future user-facing/independently runnable applications
    web/                Next.js application (not created yet)
    api/                Read-only FastAPI service for the frontend (Phase 1: flyers only)
ingestion/              Python flyer ingestion pipeline
    pyproject.toml
    src/lidl_tracker/
        acquisition.py    Schwarz leaflet API client + idempotent downloader
        pdf_extract.py    PyMuPDF -> spans with coordinates and fonts
        parsers.py        pure text -> price / quantity / unit price / units
        cards.py          spatial grouping + field extraction
        cli_acquire.py    cli_inspect.py    cli_extract.py
    tests/              58 tests, no PDF required
migrations/             database schema history (documentary; applied via inline SQL)
tools/                  one-off reverse-engineering scripts (Playwright) +
                        image_ranking/ offline research tool (own tests/)
docs/                   acquisition.md, pdf-structure.md, scheduling.md
```

## Raw data is preserved

Each card keeps `raw_text`, `page`, `bbox`, `parser_version`, `warnings`
and `notes`. Each PDF is stored with a `.meta.json` sidecar holding the API
metadata, `downloaded_at` and `content_hash`, so flyers can be reprocessed
as the parser improves.

R2 extraction JSON uses a versioned manifest that includes the metadata
needed to recreate each flyer database row. PostgreSQL IDs are generated
again during recovery; product cards, including their calculated page and
bbox, are regenerated from the stored PDF. Run `cli_restore --dry-run` to
validate manifests and PDF hashes before running `cli_restore --migrate`.
While PostgreSQL is still available, run `cli_snapshot --dry-run` and then
`cli_snapshot` to backfill versioned manifests for existing flyers; this
preserves any existing card JSON while adding database metadata.
If PostgreSQL is unavailable during ingestion's initial lookup, ingestion
preserves the PDF and metadata manifest in R2 before reporting the database
failure.
Restore does not delete existing rows; it skips existing flyers and refreshes
their product cards, so use an empty or intentionally selected database for a
full rebuild. Legacy extraction JSON cannot be used for database recovery
until it has been backfilled from the still-available database; unsupported
manifests are reported as errors.

## Not implemented yet (deliberately)

Entity resolution, appearance history, recurrence prediction, and a
production scheduler are not implemented yet. Database persistence, R2
storage, product-image storage, and notifications are implemented.
