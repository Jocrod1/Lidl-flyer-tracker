"""CLI: ingest Lidl Spain flyers into R2 + PostgreSQL.

    python -m lidl_tracker.cli_ingest

Required environment variables:
    DATABASE_URL         postgresql://user:pass@host:5432/dbname
    R2_ENDPOINT_URL      https://<account_id>.r2.cloudflarestorage.com
    R2_ACCESS_KEY_ID
    R2_SECRET_ACCESS_KEY
    R2_BUCKET_NAME

Optional:
    --migrate        apply DB migrations before running (idempotent)
    --slug/--slugs    ingest one or more flyer slugs, comma-separated
"""

from __future__ import annotations

import argparse
import logging
import sys

from .ingest import run_ingestion
from .models.flyer import FlyerStatus
from .storage import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest Lidl ES flyers → R2 + DB")
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="run DB migrations (CREATE TABLE IF NOT EXISTS) before ingesting",
    )
    parser.add_argument(
        "--slug",
        "--slugs",
        dest="slugs",
        help="comma-separated flyer slug(s) to ingest directly",
    )
    args = parser.parse_args(argv)

    if args.migrate:
        logger.info("applying database migrations …")
        db.apply_migrations()
        logger.info("migrations done")

    requested_slugs = None
    if args.slugs:
        requested_slugs = [slug.strip() for slug in args.slugs.split(",")]

    results = run_ingestion(requested_slugs)

    new = [r for r in results if not r.skipped]
    skipped = [r for r in results if r.skipped]
    failed_count = sum(1 for r in results if r.status == FlyerStatus.FAILED)

    print(f"\n{'─'*60}")
    print(f"  ingested : {len(new)}")
    print(f"  skipped  : {len(skipped)}")
    print(f"  failed   : {failed_count}")
    print(f"{'─'*60}\n")

    for r in new:
        print(f"  [NEW]     {r.flyer_meta.name}")
        print(f"            hash={r.content_hash[:16]}…  key={r.storage_key}")
    for r in skipped:
        print(f"  [SKIP]    {r.flyer_meta.name}")

    return 1 if failed_count else 0


if __name__ == "__main__":
    sys.exit(main())
