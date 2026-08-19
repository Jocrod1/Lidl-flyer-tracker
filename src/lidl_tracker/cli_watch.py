"""Weekly product watcher.

    python -m lidl_tracker.cli_watch --query "queso en salmuera" --to me@example.com

Designed to be invoked by a scheduler (see docs/scheduling.md) every Sunday.
It is safe to run more than once:

  - flyer downloads are idempotent (acquisition.py already skips existing files)
  - card extraction is cached per flyer id
  - a notification is only sent once per (flyer_id, normalized_query) pair,
    tracked in a small local JSON state file

So re-running the same day, or on a day when nothing changed, sends no
duplicate email and does no redundant PDF parsing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

from .acquisition import LidlLeafletClient
from .cards import extract_document_cards
from .notify import send_email
from .parsers import normalize_name
from .pdf_extract import extract_all
from .search import search_cards

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = Path(os.environ.get("LIDL_WATCH_RAW_DIR", ROOT / "data" / "raw"))
CACHE_DIR = Path(os.environ.get("LIDL_WATCH_CACHE_DIR", ROOT / "data" / "cache"))
STATE_PATH = Path(
    os.environ.get("LIDL_WATCH_STATE_PATH", ROOT / "data" / "state" / "watch_state.json")
)


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"notified": []}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def already_notified(state: dict[str, Any], flyer_id: str, query_key: str) -> bool:
    return [flyer_id, query_key] in state["notified"]


def mark_notified(state: dict[str, Any], flyer_id: str, query_key: str) -> None:
    state["notified"].append([flyer_id, query_key])


def extract_cards_cached(pdf_path: Path, flyer_id: str) -> list[dict[str, Any]]:
    """Extract product cards, caching per flyer id so re-runs are cheap."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{flyer_id}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    pages = extract_all(pdf_path)
    cards = [c.to_dict() for c in extract_document_cards(pages)]
    cache_file.write_text(
        json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return cards


def format_email(
    query: str,
    flyer_name: str,
    offer_start: str,
    offer_end: str,
    flyer_url: str,
    hits: list[dict[str, Any]],
) -> tuple[str, str]:
    subject = f"Lidl: '{query}' is in this week's flyer"
    lines = [
        f"'{query}' was found in {flyer_name} ({offer_start} -> {offer_end}).",
        f"Flyer: {flyer_url}",
        "",
        "Matches:",
    ]
    for card in hits:
        qty = card.get("quantity") or {}
        qty_txt = qty.get("raw") if qty else "n/a"
        lines.append(
            f"  - {card.get('brand') or ''} {card.get('name')} "
            f"({qty_txt}) - {card.get('price')} EUR "
            f"[page {card.get('page')}]"
        )
    return subject, "\n".join(lines)


def run(query: str, to_addr: str, force: bool = False) -> int:
    state = load_state()
    query_key = normalize_name(query)
    found_any = False

    with LidlLeafletClient() as client:
        flyers = client.discover()
        print(f"discovered {len(flyers)} flyers at {dt.datetime.now().isoformat()}")

        for flyer in flyers:
            pdf_path, downloaded = client.download_pdf(flyer, RAW_DIR)

            if already_notified(state, flyer.id, query_key) and not force:
                print(f"skip (already notified) : {flyer.name}")
                continue

            status = "downloaded" if downloaded else "cached"
            print(f"searching                : {flyer.name} ({status})")
            cards = extract_cards_cached(pdf_path, flyer.id)
            hits = search_cards(cards, query)

            if not hits:
                continue

            found_any = True
            subject, body = format_email(
                query,
                flyer.name,
                flyer.offer_start_date or "?",
                flyer.offer_end_date or "?",
                flyer.flyer_url,
                hits,
            )
            sent = send_email(to_addr, subject, body)
            print(f"  -> {len(hits)} match(es); email {'sent' if sent else 'dry-run'}")
            mark_notified(state, flyer.id, query_key)

    save_state(state)
    if not found_any:
        print(f"\nno flyer currently contains '{query}'")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch for a product in Lidl ES flyers")
    parser.add_argument("--query", required=True, help='e.g. "queso en salmuera"')
    parser.add_argument("--to", required=True, dest="to_addr", help="notification email")
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-check and re-notify even if this flyer was already processed",
    )
    args = parser.parse_args(argv)
    return run(args.query, args.to_addr, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
