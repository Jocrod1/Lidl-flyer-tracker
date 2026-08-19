"""Flyer ingestion pipeline.

Orchestrates the full flow:

    Discover flyers via Lidl API
        ↓
    Download PDF (streaming)
        ↓
    Calculate SHA-256
        ↓
    Idempotency check (is hash already in DB?)
        ↓ (only if new)
    Upload PDF to Cloudflare R2
        ↓
    Insert flyer metadata in PostgreSQL

The pipeline is safe to run multiple times.  Re-discovering a flyer that
was already ingested produces a log message and exits cleanly.

Failure handling
----------------
If the R2 upload succeeds but the DB insert fails, the next run will:
  1. Download the PDF again.
  2. Hash it — same hash.
  3. Find no DB record for that hash.
  4. Attempt R2 upload — R2 already has the object (same key), so it is
     simply overwritten (idempotent for identical content).
  5. Insert the DB record.

If the DB record exists but the R2 object is missing, ``ingest_flyer``
detects that and re-uploads before updating the status.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Sequence

from .acquisition import FlyerMeta, LidlLeafletClient
from .cards import extract_document_cards
from .models.flyer import FlyerRecord, FlyerStatus
from .pdf_extract import extract_all
from .storage import database as db
from .storage import r2

logger = logging.getLogger(__name__)


class IngestionResult:
    __slots__ = (
        "flyer_meta",
        "status",
        "skipped",
        "storage_key",
        "content_hash",
        "flyer_existing",
        "pdf_existing",
        "extracted_cards",
        "persisted_cards",
        "extraction_key",
    )

    def __init__(
        self,
        flyer_meta: FlyerMeta,
        status: FlyerStatus,
        skipped: bool,
        storage_key: str,
        content_hash: str,
        *,
        flyer_existing: bool = False,
        pdf_existing: bool = False,
        extracted_cards: int = 0,
        persisted_cards: int = 0,
        extraction_key: str = "",
    ) -> None:
        self.flyer_meta = flyer_meta
        self.status = status
        self.skipped = skipped
        self.storage_key = storage_key
        self.content_hash = content_hash
        self.flyer_existing = flyer_existing
        self.pdf_existing = pdf_existing
        self.extracted_cards = extracted_cards
        self.persisted_cards = persisted_cards
        self.extraction_key = extraction_key

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"IngestionResult(name={self.flyer_meta.name!r}, "
            f"status={self.status}, skipped={self.skipped})"
        )


def _download_pdf_bytes(client: LidlLeafletClient, pdf_url: str) -> bytes:
    """Download *pdf_url* and return the raw bytes."""
    with client._client.stream("GET", pdf_url) as resp:
        resp.raise_for_status()
        return resp.read()


def _extract_cards_from_pdf_bytes(pdf_bytes: bytes) -> list[dict]:
    """Run the existing extraction algorithm and return card dicts."""
    with tempfile.TemporaryDirectory(prefix="lidl-flyer-") as tmpdir:
        pdf_path = Path(tmpdir) / "flyer.pdf"
        pdf_path.write_bytes(pdf_bytes)
        pages = extract_all(pdf_path)
    return [card.to_dict() for card in extract_document_cards(pages)]


def _card_hash(card: dict) -> str:
    raw = json.dumps(card, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _persist_extraction(
    flyer_record: FlyerRecord,
    content_hash: str,
    pdf_bytes: bytes,
) -> tuple[int, int, str]:
    cards = _extract_cards_from_pdf_bytes(pdf_bytes)
    cards_with_hash = [{**card, "card_hash": _card_hash(card)} for card in cards]

    extraction_key = r2.extraction_key_for_pdf_key(flyer_record.storage_key)
    payload = {
        "flyer_id": flyer_record.id,
        "content_hash": content_hash,
        "pdf_storage_key": flyer_record.storage_key,
        "card_count": len(cards_with_hash),
        "cards": cards_with_hash,
    }
    r2.upload_json(extraction_key, payload)

    if flyer_record.id is None:
        raise RuntimeError("flyer id is required to persist extracted cards")
    db.upsert_product_cards(flyer_record.id, cards_with_hash)
    return len(cards_with_hash), len(cards_with_hash), extraction_key


def ingest_flyer(
    flyer: FlyerMeta,
    client: LidlLeafletClient,
    *,
    now: dt.datetime | None = None,
) -> IngestionResult:
    """Ingest one flyer: download → hash → R2 → DB.

    Returns an IngestionResult describing what happened.
    Raises on unrecoverable errors.
    """
    if now is None:
        now = dt.datetime.now(dt.timezone.utc)

    year = now.strftime("%Y")
    month = now.strftime("%m")

    # --- Step 1: download PDF ---
    logger.info("downloading PDF: %s", flyer.pdf_url)
    pdf_bytes = _download_pdf_bytes(client, flyer.pdf_url)
    downloaded_at = dt.datetime.now(dt.timezone.utc)

    # --- Step 2: hash ---
    content_hash = r2.sha256_bytes(pdf_bytes)
    storage_key = r2.object_key_for_hash(content_hash, year, month)
    logger.info("content_hash=%s  storage_key=%s", content_hash, storage_key)

    # --- Step 3: idempotency check ---
    existing = db.get_flyer_by_hash(content_hash)
    if existing is not None:
        logger.info("already ingested (hash match): %s", flyer.name)
        flyer_record = existing
        storage_key = flyer_record.storage_key
        # If R2 object is somehow missing, re-upload it.
        pdf_already_exists = r2.object_exists(storage_key)
        if not pdf_already_exists:
            logger.warning("DB record exists but R2 object missing — re-uploading")
            r2.upload_pdf(storage_key, pdf_bytes)
        extracted_cards, persisted_cards, extraction_key = _persist_extraction(
            flyer_record, content_hash, pdf_bytes
        )
        logger.info(
            "ingestion_result slug=%s pdf_sha256=%s flyer=%s pdf=%s extracted_cards=%d persisted_cards=%d extraction_json_key=%s",
            flyer.slug,
            content_hash,
            "existing",
            "existing" if pdf_already_exists else "new",
            extracted_cards,
            persisted_cards,
            extraction_key,
        )
        return IngestionResult(
            flyer_meta=flyer,
            status=existing.status,
            skipped=True,
            storage_key=storage_key,
            content_hash=content_hash,
            flyer_existing=True,
            pdf_existing=pdf_already_exists,
            extracted_cards=extracted_cards,
            persisted_cards=persisted_cards,
            extraction_key=extraction_key,
        )

    # --- Step 4: upload to R2 ---
    pdf_already_exists = r2.object_exists(storage_key)
    logger.info("uploading to R2: %s", storage_key)
    r2.upload_pdf(storage_key, pdf_bytes)
    if not r2.verify_upload(storage_key, content_hash):
        raise RuntimeError(f"R2 upload verification failed for {storage_key}")

    # --- Step 5: insert DB record ---
    record = FlyerRecord(
        source_url=flyer.pdf_url,
        storage_key=storage_key,
        category=flyer.category,
        name=flyer.name,
        start_date=flyer.start_date,
        end_date=flyer.end_date,
        content_hash=content_hash,
        downloaded_at=downloaded_at,
        status=FlyerStatus.STORED,
    )
    flyer_record = db.insert_flyer(record)
    logger.info("ingested flyer: %s (id=%s)", flyer.name, flyer_record.id)
    extracted_cards, persisted_cards, extraction_key = _persist_extraction(
        flyer_record, content_hash, pdf_bytes
    )
    logger.info(
        "ingestion_result slug=%s pdf_sha256=%s flyer=%s pdf=%s extracted_cards=%d persisted_cards=%d extraction_json_key=%s",
        flyer.slug,
        content_hash,
        "new",
        "existing" if pdf_already_exists else "new",
        extracted_cards,
        persisted_cards,
        extraction_key,
    )

    return IngestionResult(
        flyer_meta=flyer,
        status=FlyerStatus.STORED,
        skipped=False,
        storage_key=storage_key,
        content_hash=content_hash,
        flyer_existing=False,
        pdf_existing=pdf_already_exists,
        extracted_cards=extracted_cards,
        persisted_cards=persisted_cards,
        extraction_key=extraction_key,
    )


def run_ingestion(slugs: Sequence[str] | None = None) -> list[IngestionResult]:
    """Ingest currently advertised flyers or fetch specific flyers by slug."""
    results: list[IngestionResult] = []
    requested_slugs = _normalize_slugs(slugs)
    with LidlLeafletClient() as client:
        if requested_slugs is None:
            flyers = client.discover()
            logger.info("discovered %d flyers", len(flyers))
        else:
            flyers = []
            for slug in requested_slugs:
                try:
                    flyers.append(client.fetch_flyer_meta(slug))
                except Exception:
                    logger.exception("failed to fetch flyer slug %s", slug)
            logger.info("fetched %d requested flyers", len(flyers))
        for flyer in flyers:
            try:
                result = ingest_flyer(flyer, client)
                results.append(result)
            except Exception:
                logger.exception("failed to ingest flyer %s", flyer.name)
    return results


def run_ingestion_by_slug(slugs: Sequence[str] | None = None) -> list[IngestionResult]:
    """Backward-compatible alias for slug-aware ingestion."""
    return run_ingestion(slugs)


def _normalize_slugs(slugs: Sequence[str] | None) -> list[str] | None:
    if slugs is None:
        return None
    normalized = [slug.strip().lower() for slug in slugs if slug and slug.strip()]
    if not normalized:
        return None
    return list(dict.fromkeys(normalized))
