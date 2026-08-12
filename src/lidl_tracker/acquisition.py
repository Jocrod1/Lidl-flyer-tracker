"""Acquisition client for Lidl Spain flyers.

Talks directly to the Schwarz Group leaflet API that powers the Lidl ES
flyer viewer. The endpoint and parameters below were captured from real
network traffic (see `tools/capture_network.py` and `docs/acquisition.md`),
not guessed.

    GET https://endpoints.leaflets.schwarz/v4/overview
        ?client_locale=lidl/es-ES&region_id=0

    GET https://endpoints.leaflets.schwarz/v4/flyer
        ?flyer_identifier=<slug>&region_id=0

The overview response already contains a direct `pdfUrl`, so no browser
automation is needed in production.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator

import httpx

API_BASE = "https://endpoints.leaflets.schwarz/v4"
CLIENT_LOCALE = "lidl/es-ES"
DEFAULT_REGION_ID = 0

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_SLUG_RE = re.compile(r"/l/folletos/([^/]+)/")


@dataclasses.dataclass(frozen=True)
class FlyerMeta:
    """Metadata for a single flyer as advertised by the leaflet API."""

    id: str
    slug: str
    name: str
    title: str
    category: str
    subcategory: str
    pdf_url: str
    flyer_url: str
    start_date: str | None
    end_date: str | None
    offer_start_date: str | None
    offer_end_date: str | None
    status: str
    file_size: int | None
    discovered_at: str

    @property
    def identity_hash(self) -> str:
        """Stable identifier derived from the PDF URL.

        The API `id` is already a UUID, but hashing the asset URL lets us
        detect the case where a previously discovered flyer starts pointing
        at a different asset.
        """
        return hashlib.sha256(self.pdf_url.encode("utf-8")).hexdigest()[:16]

    @property
    def pdf_filename(self) -> str:
        return f"{self.id}__{Path(self.pdf_url).name}"

    def to_dict(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        data["identity_hash"] = self.identity_hash
        return data


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _slug_from_url(url: str) -> str:
    match = _SLUG_RE.search(url or "")
    return match.group(1) if match else ""


class LidlLeafletClient:
    """Thin, dependency-light client around the Schwarz leaflet API."""

    def __init__(
        self,
        client_locale: str = CLIENT_LOCALE,
        region_id: int = DEFAULT_REGION_ID,
        timeout: float = 60.0,
    ) -> None:
        self.client_locale = client_locale
        self.region_id = region_id
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "LidlLeafletClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- raw calls -----------------------------------------------------

    def fetch_overview(self) -> dict[str, Any]:
        resp = self._client.get(
            f"{API_BASE}/overview",
            params={"client_locale": self.client_locale, "region_id": self.region_id},
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_flyer(self, slug: str) -> dict[str, Any]:
        """Full flyer document, including per-page metadata and keywords."""
        resp = self._client.get(
            f"{API_BASE}/flyer",
            params={"flyer_identifier": slug, "region_id": self.region_id},
        )
        resp.raise_for_status()
        return resp.json()

    # -- discovery -----------------------------------------------------

    def discover(self) -> list[FlyerMeta]:
        """Return all flyers currently advertised for Lidl Spain."""
        overview = self.fetch_overview()
        discovered_at = _now()
        flyers: list[FlyerMeta] = []

        for category in overview.get("categories") or []:
            category_name = category.get("name") or ""
            for subcategory in category.get("subcategories") or []:
                subcategory_name = subcategory.get("name") or ""
                for raw in subcategory.get("flyers") or []:
                    pdf_url = raw.get("hiResPdfUrl") or raw.get("pdfUrl") or ""
                    if not pdf_url:
                        continue
                    flyer_url = raw.get("flyerUrlAbsolute") or ""
                    flyers.append(
                        FlyerMeta(
                            id=raw.get("id") or "",
                            slug=_slug_from_url(flyer_url),
                            name=raw.get("name") or "",
                            title=raw.get("title") or "",
                            category=category_name,
                            subcategory=subcategory_name,
                            pdf_url=pdf_url,
                            flyer_url=flyer_url,
                            start_date=raw.get("startDate"),
                            end_date=raw.get("endDate"),
                            offer_start_date=raw.get("offerStartDate"),
                            offer_end_date=raw.get("offerEndDate"),
                            status=raw.get("status") or "",
                            file_size=raw.get("hiResFileSize") or raw.get("fileSize"),
                            discovered_at=discovered_at,
                        )
                    )
        return flyers

    # -- download ------------------------------------------------------

    def download_pdf(
        self, flyer: FlyerMeta, dest_dir: Path, force: bool = False
    ) -> tuple[Path, bool]:
        """Download a flyer PDF idempotently.

        Returns (path, downloaded) where `downloaded` is False when a valid
        local copy already existed.
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / flyer.pdf_filename

        if target.exists() and not force:
            if flyer.file_size is None or target.stat().st_size == flyer.file_size:
                return target, False

        tmp = target.with_suffix(target.suffix + ".part")
        with self._client.stream("GET", flyer.pdf_url) as resp:
            resp.raise_for_status()
            with tmp.open("wb") as handle:
                for chunk in resp.iter_bytes(chunk_size=1 << 16):
                    handle.write(chunk)
        tmp.replace(target)

        sidecar = target.with_suffix(".meta.json")
        payload = flyer.to_dict()
        payload["downloaded_at"] = _now()
        payload["content_hash"] = sha256_file(target)
        payload["local_path"] = str(target)
        sidecar.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return target, True


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_flyer_page_keywords(flyer_doc: dict[str, Any]) -> Iterator[tuple[int, str]]:
    """Yield (page_number, keywords) from a /v4/flyer response.

    Useful as an independent cross-check against PDF text extraction.
    """
    for page in (flyer_doc.get("flyer") or {}).get("pages") or []:
        yield page.get("number", 0), page.get("keyWords") or ""
