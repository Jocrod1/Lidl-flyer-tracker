# Lidl Spain flyer product tracker

Milestones 1–5 of the incremental plan: flyer acquisition, PDF inspection,
product-card grouping, deterministic field extraction and measurement.

**No OCR, no object detection, no LLM, no embeddings.** They were not
needed — see `docs/pdf-structure.md` for why.

## Setup

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

## Usage

```bash
# Milestone 1 — discover flyers and download PDFs (idempotent)
python -m lidl_tracker.cli_acquire --list
python -m lidl_tracker.cli_acquire --download-all
python -m lidl_tracker.cli_ingest --slug folleto-alimentacion-17-8-17-8-26-23-8-26-a07bd0
python -m lidl_tracker.cli_ingest --slug folleto-alimentacion-17-8-17-8-26-23-8-26-a07bd0,folleto-bazar-17-8-17-8-26-23-8-26-e0c443
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

pytest
```

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
src/lidl_tracker/
    acquisition.py    Schwarz leaflet API client + idempotent downloader
    pdf_extract.py    PyMuPDF -> spans with coordinates and fonts
    parsers.py        pure text -> price / quantity / unit price / units
    cards.py          spatial grouping + field extraction
    cli_acquire.py    cli_inspect.py    cli_extract.py
tools/                one-off reverse-engineering scripts (Playwright)
docs/                 acquisition.md, pdf-structure.md
tests/                58 tests, no PDF required
```

## Raw data is preserved

Each card keeps `raw_text`, `page`, `bbox`, `parser_version`, `warnings`
and `notes`. Each PDF is stored with a `.meta.json` sidecar holding the API
metadata, `downloaded_at` and `content_hash`, so flyers can be reprocessed
as the parser improves.

## Not implemented yet (deliberately)

Database persistence, entity resolution, appearance history, recurrence
prediction, notifications, scheduler.
