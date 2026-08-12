"""Dump flyer links from the rendered Lidl ES overview page."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OVERVIEW = "https://www.lidl.es/c/descubre-nuevas-ofertas-cada-semana-folletos-lidl/s10087402"
OUT = Path(__file__).resolve().parents[1] / "data" / "recon"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(locale="es-ES").new_page()
        page.goto(OVERVIEW, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(3000)

        links = page.eval_on_selector_all(
            "a",
            """els => els.map(e => ({
                href: e.href,
                text: (e.innerText || '').trim().slice(0, 120),
            })).filter(l => /folleto|leaflet|flyer/i.test(l.href))""",
        )
        html = page.content()
        browser.close()

    (OUT / "overview_rendered.html").write_text(html, encoding="utf-8")
    (OUT / "flyer_links.json").write_text(
        json.dumps(links, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"{len(links)} flyer links\n")
    seen = set()
    for link in links:
        if link["href"] in seen:
            continue
        seen.add(link["href"])
        print(f"{link['href']}\n    {link['text']!r}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
