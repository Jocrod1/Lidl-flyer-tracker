"""Reverse-engineer Lidl ES flyer delivery by capturing real network traffic.

Opens the flyer overview page and one flyer detail page in Chromium, records
every request, and reports those relevant to the Schwarz leaflet backend.

Usage:
    python tools/capture_network.py [flyer_path]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OVERVIEW = "https://www.lidl.es/c/descubre-nuevas-ofertas-cada-semana-folletos-lidl/s10087402"
DEFAULT_FLYER = "/folletos/folleto-alimentacion-17-8-17-8-26-23-8-26-a07bd0/ar/0"

INTERESTING = (
    "leaflet",
    "flyer",
    "folleto",
    "brochure",
    "onstackit",
    "object.storage",
    ".pdf",
    "overview",
)

OUT = Path(__file__).resolve().parents[1] / "data" / "recon"


def interesting(url: str) -> bool:
    low = url.lower()
    return any(token in low for token in INTERESTING)


def main() -> int:
    flyer_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FLYER
    flyer_url = "https://www.lidl.es" + flyer_path

    OUT.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-ES",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
        )

        def on_response(response) -> None:
            url = response.url
            if not interesting(url):
                return
            entry = {
                "url": url,
                "method": response.request.method,
                "status": response.status,
                "content_type": response.headers.get("content-type", ""),
                "resource_type": response.request.resource_type,
            }
            if "json" in entry["content_type"]:
                try:
                    entry["body"] = response.text()[:200000]
                except Exception as exc:  # noqa: BLE001
                    entry["body_error"] = str(exc)
            records.append(entry)

        context.on("response", on_response)
        page = context.new_page()

        for target in (OVERVIEW, flyer_url):
            print(f"\n=== visiting {target} ===")
            page.goto(target, wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(4000)

        browser.close()

    (OUT / "network.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\ncaptured {len(records)} interesting responses\n")
    for rec in records:
        if rec["resource_type"] in {"image", "font", "stylesheet"}:
            continue
        print(f"{rec['status']} {rec['resource_type']:10} {rec['content_type'][:30]:32} {rec['url'][:150]}")

    print(f"\nfull log -> {OUT / 'network.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
