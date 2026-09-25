"""CLI: restore flyer and product-card database data from R2."""

from __future__ import annotations

import argparse
import logging
import sys

from .recovery import restore_from_r2
from .storage import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Restore flyer metadata and regenerate product cards from R2"
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="apply idempotent database migrations before restoring",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate manifests and PDFs without changing the database or R2",
    )
    parser.add_argument(
        "--prefix",
        default="flyers/",
        help="R2 key prefix to scan (default: flyers/)",
    )
    args = parser.parse_args(argv)

    try:
        if args.migrate and not args.dry_run:
            db.apply_migrations()
        results = restore_from_r2(dry_run=args.dry_run, prefix=args.prefix)
    except Exception:
        logger.exception("R2 database restore failed")
        return 1

    restored = sum(result.restored_flyer for result in results)
    print(f"manifests validated: {len(results)}")
    if not args.dry_run:
        print(f"flyer rows restored: {restored}")
        print(f"product cards regenerated: {sum(result.card_count or 0 for result in results)}")
    else:
        print(f"flyer rows that would be created (database not checked): {len(results)}")
    for result in results:
        if args.dry_run:
            action = "VALID"
        else:
            action = "RESTORE" if result.restored_flyer else "REFRESH"
        print(f"[{action}] {result.name}  hash={result.content_hash}  key={result.extraction_key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
