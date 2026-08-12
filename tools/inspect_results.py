"""Inspect extraction results: sample partial cards and search products."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=Path)
    parser.add_argument("--warning", help="show cards with this warning")
    parser.add_argument("--search", help="substring of normalized name")
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args(argv)

    cards = json.loads(args.json_path.read_text(encoding="utf-8"))

    if args.search:
        needle = args.search.lower()
        hits = [
            c
            for c in cards
            if needle in (c.get("normalized_name") or "")
            or needle in (c.get("raw_text") or "").lower()
        ]
        print(f"{len(hits)} matches for {args.search!r}\n")
        for card in hits[: args.limit]:
            print(json.dumps(card, indent=2, ensure_ascii=False))
        return 0

    if args.warning:
        hits = [c for c in cards if args.warning in c["warnings"]]
        print(f"{len(hits)} cards with warning {args.warning!r}\n")
        for card in hits[: args.limit]:
            print(
                f"p{card['page']:>3} brand={card['brand']!r} name={card['name']!r}\n"
                f"      qty={card['quantity']} price={card['price']} "
                f"unit={card['unit_prices']}\n"
                f"      raw={card['raw_text']!r}\n"
            )
        return 0

    brands = collections.Counter(c["brand"] for c in cards if c["brand"])
    print("top brands")
    for brand, count in brands.most_common(25):
        print(f"  {brand:<28} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
