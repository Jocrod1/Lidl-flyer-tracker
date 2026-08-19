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
import logging
from pathlib import Path

from .acquisition import FlyerMeta, LidlLeafletClient
from .models.flyer import FlyerRecord, FlyerStatus
from .storage import database as db
from .storage import r2

logger = logging.getLogger(__name__)


class IngestionResult:
    __slots__ = ("flyer_meta", "status", "skipped", "storage_key", "content_hash")

    def __init__(
        self,
        flyer_meta: FlyerMeta,
        status: FlyerStatus,
        skipped: bool,
        storage_key: str,
        content_hash: str,
    ) -> None:
        self.flyer_meta = flyer_meta
        self.status = status
        self.skipped = skipped
        self.storage_key = storage_key
        self.content_hash = content_hash

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
        # If R2 object is somehow missing, re-upload it.
        if not r2.object_exists(storage_key):
            logger.warning("DB record exists but R2 object missing — re-uploading")
            r2.upload_pdf(storage_key, pdf_bytes)
        return IngestionResult(
            flyer_meta=flyer,
            status=existing.status,
            skipped=True,
            storage_key=storage_key,
            content_hash=content_hash,
        )

    # --- Step 4: upload to R2 ---
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
    db.insert_flyer(record)
    logger.info("ingested flyer: %s (id=%s)", flyer.name, record.id)

    return IngestionResult(
        flyer_meta=flyer,
        status=FlyerStatus.STORED,
        skipped=False,
        storage_key=storage_key,
        content_hash=content_hash,
    )


def run_ingestion() -> list[IngestionResult]:
    """Discover all current Lidl ES flyers and ingest any that are new."""
    results: list[IngestionResult] = []
    with LidlLeafletClient() as client:
        flyers = client.discover()
        logger.info("discovered %d flyers", len(flyers))
        for flyer in flyers:
            try:
                result = ingest_flyer(flyer, client)
                results.append(result)
            except Exception:
                logger.exception("failed to ingest flyer %s", flyer.name)
    return results
