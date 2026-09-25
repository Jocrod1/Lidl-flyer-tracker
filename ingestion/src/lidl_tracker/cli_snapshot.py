"""CLI: backfill durable R2 manifests from the current PostgreSQL data."""

from __future__ import annotations

import argparse
import logging
import sys

from .recovery import backfill_r2_manifests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill versioned R2 flyer manifests from PostgreSQL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate database rows and R2 PDFs without writing manifests",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="database flyer rows to process per page (default: 500)",
    )
    args = parser.parse_args(argv)

    try:
        results = backfill_r2_manifests(
            dry_run=args.dry_run,
            page_size=args.page_size,
        )
    except Exception:
        logger.exception("R2 manifest backfill failed")
        return 1

    print(f"flyer manifests {'validated' if args.dry_run else 'written'}: {len(results)}")
    for result in results:
        action = "VALID" if args.dry_run else "BACKFILLED"
        print(f"[{action}] {result.name}  hash={result.content_hash}  key={result.extraction_key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
