"""CLI: discover and download Lidl Spain flyers.

    python -m lidl_tracker.cli_acquire --list
    python -m lidl_tracker.cli_acquire --download-all
    python -m lidl_tracker.cli_acquire --download <flyer-id-or-substring>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .acquisition import LidlLeafletClient

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lidl ES flyer acquisition")
    parser.add_argument("--list", action="store_true", help="list discovered flyers")
    parser.add_argument("--download-all", action="store_true")
    parser.add_argument("--download", metavar="MATCH", help="id/name substring")
    parser.add_argument("--force", action="store_true", help="re-download")
    parser.add_argument("--dest", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)

    with LidlLeafletClient() as client:
        flyers = client.discover()
        print(f"discovered {len(flyers)} flyers\n")

        for flyer in flyers:
            print(f"[{flyer.status:8}] {flyer.id}")
            print(f"    name       : {flyer.name}  ({flyer.title})")
            print(f"    category   : {flyer.category} / {flyer.subcategory}")
            print(f"    offer      : {flyer.offer_start_date} -> {flyer.offer_end_date}")
            print(f"    valid      : {flyer.start_date} -> {flyer.end_date}")
            print(f"    size       : {flyer.file_size}")
            print(f"    hash       : {flyer.identity_hash}")
            print(f"    pdf        : {flyer.pdf_url}")
            print()

        targets = []
        if args.download_all:
            targets = flyers
        elif args.download:
            needle = args.download.lower()
            targets = [
                f
                for f in flyers
                if needle in f.id.lower()
                or needle in f.name.lower()
                or needle in f.slug.lower()
            ]
            if not targets:
                print(f"no flyer matches {args.download!r}", file=sys.stderr)
                return 1

        for flyer in targets:
            path, downloaded = client.download_pdf(flyer, args.dest, force=args.force)
            state = "downloaded" if downloaded else "cached"
            print(f"{state:10} {path.name}  ({path.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
