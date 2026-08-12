"""CLI: extract product cards from a flyer PDF and report parse quality.

    python -m lidl_tracker.cli_extract <pdf>
    python -m lidl_tracker.cli_extract <pdf> --page 13 --show
    python -m lidl_tracker.cli_extract <pdf> --failures
    python -m lidl_tracker.cli_extract <pdf> --json out.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from .cards import extract_document_cards
from .pdf_extract import extract_all


def render(card) -> str:
    parts = [f"  [{card.status}] page {card.page}"]
    parts.append(f"    brand      : {card.brand}")
    parts.append(f"    name       : {card.name}")
    parts.append(f"    description: {card.description}")
    if card.quantity:
        q = card.quantity
        parts.append(
            f"    quantity   : value={q.value} unit={q.unit} count={q.count} raw={q.raw!r}"
        )
    else:
        parts.append("    quantity   : None")
    parts.append(f"    price      : {card.price} EUR (lidl_plus={card.lidl_plus})")
    parts.append(f"    reference  : {card.reference_price}")
    parts.append(
        "    unit_price : "
        + (", ".join(f"{u.value} EUR/{u.unit}" for u in card.unit_prices) or "None")
    )
    parts.append(f"    discount   : {card.discount_percent}")
    if card.warnings:
        parts.append(f"    warnings   : {', '.join(card.warnings)}")
    if card.notes:
        parts.append(f"    notes      : {', '.join(card.notes)}")
    parts.append(f"    raw_text   : {card.raw_text!r}")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract products from a Lidl flyer")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--page", type=int, help="restrict to one page")
    parser.add_argument("--show", action="store_true", help="print every card")
    parser.add_argument("--failures", action="store_true", help="print failed/partial")
    parser.add_argument("--json", type=Path, help="write all cards to JSON")
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(f"not found: {args.pdf}", file=sys.stderr)
        return 1

    pages = extract_all(args.pdf)
    if args.page:
        pages = [p for p in pages if p.number == args.page]

    cards = extract_document_cards(pages)

    counts = collections.Counter(c.status for c in cards)
    total = len(cards)
    ok = counts["ok"]
    partial = counts["partial"]
    failed = counts["failed"]

    print("=" * 62)
    print(f"file            : {args.pdf.name}")
    print(f"pages           : {len(pages)}")
    print(f"candidate cards : {total}")
    print(f"parsed fully    : {ok}")
    print(f"partial         : {partial}")
    print(f"failed          : {failed}")
    if total:
        print(f"usable rate     : {(ok + partial) / total * 100:.1f}%")
        print(f"full rate       : {ok / total * 100:.1f}%")

    field_hits = collections.Counter()
    for card in cards:
        field_hits["name"] += bool(card.name)
        field_hits["brand"] += bool(card.brand)
        field_hits["price"] += card.price is not None
        field_hits["quantity"] += card.quantity is not None
        field_hits["unit_price"] += bool(card.unit_prices)
        field_hits["description"] += bool(card.description)

    print("\nfield coverage")
    for field in ("name", "brand", "price", "quantity", "unit_price", "description"):
        hits = field_hits[field]
        pct = hits / total * 100 if total else 0
        print(f"  {field:<12} {hits:>4}/{total}  {pct:5.1f}%")

    warnings = collections.Counter(w for c in cards for w in c.warnings)
    if warnings:
        print("\nwarning breakdown (quality defects)")
        for warning, count in warnings.most_common():
            print(f"  {warning:<32} {count}")

    notes = collections.Counter(n for c in cards for n in c.notes)
    if notes:
        print("\nnote breakdown (field absent, often legitimately)")
        for note, count in notes.most_common():
            print(f"  {note:<32} {count}")

    if args.show:
        print("\n" + "=" * 62)
        for card in cards:
            print(render(card))
            print()

    if args.failures:
        print("\n" + "=" * 62)
        print("FAILED / PARTIAL CARDS")
        for card in cards:
            if card.status != "ok":
                print(render(card))
                print()

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps([c.to_dict() for c in cards], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nwrote {total} cards -> {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
