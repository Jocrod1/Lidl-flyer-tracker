"""Summarise the captured leaflet API responses and verify the overview endpoint."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

RECON = Path(__file__).resolve().parents[1] / "data" / "recon"
API = "https://endpoints.leaflets.schwarz/v4"
CLIENT_LOCALE = "lidl/es-ES"

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def show_captured_flyer() -> None:
    records = json.loads((RECON / "network.json").read_text(encoding="utf-8"))
    for rec in records:
        if "/v4/flyer" in rec["url"] and "body" in rec:
            body = json.loads(rec["body"])
            (RECON / "flyer_response.json").write_text(
                json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print("=== captured /v4/flyer response ===")
            print("top-level keys:", list(body))
            data = body.get("data") or body
            if isinstance(data, list) and data:
                data = data[0]
            if isinstance(data, dict):
                for key, value in data.items():
                    preview = json.dumps(value, ensure_ascii=False)
                    if len(preview) > 160:
                        preview = preview[:160] + "..."
                    print(f"  {key}: {preview}")
            pdfs = sorted(set(re.findall(r'https?://[^"\s]+\.pdf', rec["body"])))
            print(f"\nPDF urls found: {len(pdfs)}")
            for url in pdfs[:10]:
                print("   ", url)
            return
    print("no /v4/flyer body captured")


def probe_overview() -> None:
    print("\n=== live /v4/overview with client_locale=lidl/es-ES ===")
    resp = httpx.get(
        f"{API}/overview",
        params={"client_locale": CLIENT_LOCALE, "region_id": 0, "region_code": 0},
        headers=HEADERS,
        timeout=40,
    )
    print("status:", resp.status_code)
    body = resp.json()
    (RECON / "overview_response.json").write_text(
        json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("keys:", list(body))
    print("entries:", body.get("numberOfEntries"))
    data = body.get("data") or []
    for item in data[:12] if isinstance(data, list) else []:
        if isinstance(item, dict):
            print(
                "  -",
                item.get("identifier") or item.get("id"),
                "|",
                item.get("title") or item.get("name"),
                "|",
                item.get("validFrom") or item.get("valid_from"),
                "->",
                item.get("validTo") or item.get("valid_to"),
            )


if __name__ == "__main__":
    show_captured_flyer()
    probe_overview()
