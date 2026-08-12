"""Probe the Lidl ES flyer page HTML for embedded leaflet API config.

Pure-HTTP reconnaissance step (no browser). Prints any hints about the
underlying Schwarz leaflet infrastructure found in the server-rendered HTML.
"""

import re
import sys

import httpx

PAGE = "https://www.lidl.es/c/descubre-nuevas-ofertas-cada-semana-folletos-lidl/s10087402"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}

PATTERNS = {
    "client_locale": r"client_locale[\"'=:&\s]{1,4}([A-Za-z_\-]+)",
    "locale_generic": r"[\"']locale[\"']\s*:\s*[\"']([A-Za-z_\-]+)[\"']",
    "leaflets_url": r"https?://[^\"'<>\s\\]*leaflets[^\"'<>\s\\]{0,140}",
    "stackit_url": r"https?://[^\"'<>\s\\]*onstackit[^\"'<>\s\\]{0,140}",
    "pdf_url": r"https?://[^\"'<>\s\\]*\.pdf",
    "flyer_href": r"/folletos?[^\"'<>\s\\]{0,120}",
}


def main() -> int:
    resp = httpx.get(PAGE, headers=HEADERS, timeout=40, follow_redirects=True)
    html = resp.text
    print(f"status={resp.status_code} bytes={len(html)} final_url={resp.url}")

    for name, pattern in PATTERNS.items():
        hits = sorted(set(re.findall(pattern, html)))
        print(f"\n[{name}] {len(hits)} unique")
        for hit in hits[:15]:
            print("   ", hit)

    return 0


if __name__ == "__main__":
    sys.exit(main())
