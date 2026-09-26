"""Flyer ingestion pipeline.

Orchestrates the full flow:

    Discover flyers via Lidl API
        ↓
    Download PDF (streaming)
        ↓
    Calculate SHA-256
        ↓
    Idempotency check (is hash already in DB or represented by an R2 manifest?)
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
  4. Find the matching R2 manifest by content hash and reuse its PDF key,
     or upload the PDF and create a manifest if none exists.
  5. Insert the DB record and regenerate product cards.

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
from typing import Any, Sequence

from botocore.exceptions import ClientError

from .acquisition import FlyerMeta, LidlLeafletClient
from .cards import extract_document_cards
from .models.flyer import FlyerRecord, FlyerStatus
from .pdf_extract import extract_all
from .product_images import extract_card_image, object_key_for_card
from .slugs import flyer_slug
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
        "error",
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
        error: str = "",
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
        self.error = error

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


def _flyer_snapshot_payload(
    flyer_record: FlyerRecord,
    acquisition_metadata: dict[str, Any],
    *,
    cards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the versioned R2 snapshot without relying on a database ID."""
    return {
        "schema_version": 1,
        "flyer": {
            "source_url": flyer_record.source_url,
            "storage_key": flyer_record.storage_key,
            "category": flyer_record.category,
            "name": flyer_record.name,
            "start_date": flyer_record.start_date,
            "end_date": flyer_record.end_date,
            "content_hash": flyer_record.content_hash,
            "downloaded_at": (
                flyer_record.downloaded_at.isoformat()
                if flyer_record.downloaded_at is not None
                else None
            ),
            "status": flyer_record.status.value,
            "slug": flyer_record.slug,
        },
        "acquisition": acquisition_metadata,
        # Retained for compatibility with existing extraction JSON readers.
        "flyer_id": flyer_record.id,
        "content_hash": flyer_record.content_hash,
        "pdf_storage_key": flyer_record.storage_key,
        "card_count": len(cards) if cards is not None else 0,
        "cards": cards or [],
    }


def _upload_flyer_snapshot(flyer_record: FlyerRecord, flyer: FlyerMeta) -> str:
    extraction_key = r2.extraction_key_for_pdf_key(flyer_record.storage_key)
    r2.upload_json(extraction_key, _flyer_snapshot_payload(flyer_record, flyer.to_dict()))
    return extraction_key


def _new_flyer_record(
    flyer: FlyerMeta,
    storage_key: str,
    content_hash: str,
    downloaded_at: dt.datetime,
) -> FlyerRecord:
    return FlyerRecord(
        source_url=flyer.pdf_url,
        storage_key=storage_key,
        category=flyer.category,
        name=flyer.name,
        start_date=flyer.start_date,
        end_date=flyer.end_date,
        content_hash=content_hash,
        downloaded_at=downloaded_at,
        status=FlyerStatus.STORED,
        slug=flyer_slug(flyer.category, flyer.name, flyer.start_date, content_hash),
    )


def _ensure_pdf_in_r2(storage_key: str, content_hash: str, pdf_bytes: bytes) -> bool:
    pdf_already_exists = r2.object_exists(storage_key)
    if not pdf_already_exists:
        r2.upload_pdf(storage_key, pdf_bytes)
        if not r2.verify_upload(storage_key, content_hash):
            raise RuntimeError(f"R2 upload verification failed for {storage_key}")
    return pdf_already_exists


def _find_r2_snapshot(content_hash: str) -> str | None:
    manifest_name = f"{content_hash}.cards.json"
    keys = sorted(
        key
        for key in r2.list_objects("flyers/")
        if key.rsplit("/", 1)[-1] == manifest_name
    )
    if not keys:
        return None

    key = keys[-1]
    try:
        manifest = json.loads(r2.download_object(key).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid R2 extraction manifest {key}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("content_hash") != content_hash:
        raise ValueError(f"R2 extraction manifest {key} has an invalid content_hash")
    schema_version = manifest.get("schema_version")
    if schema_version is not None and schema_version != 1:
        raise ValueError(f"R2 extraction manifest {key} has an unsupported schema_version")

    expected_pdf_key = f"{key[:-len('.cards.json')]}.pdf"
    snapshot_pdf_key = manifest.get("pdf_storage_key")
    if schema_version == 1 and snapshot_pdf_key is None:
        raise ValueError(f"R2 extraction manifest {key} is missing pdf_storage_key")
    if snapshot_pdf_key is not None and snapshot_pdf_key != expected_pdf_key:
        raise ValueError(f"R2 extraction manifest {key} references a different PDF")
    flyer = manifest.get("flyer")
    if schema_version == 1 and not isinstance(flyer, dict):
        raise ValueError(f"R2 extraction manifest {key} is missing flyer metadata")
    if flyer is not None:
        if not isinstance(flyer, dict):
            raise ValueError(f"R2 extraction manifest {key} has invalid flyer metadata")
        if flyer.get("content_hash") != content_hash or flyer.get("storage_key") != expected_pdf_key:
            raise ValueError(f"R2 extraction manifest {key} has inconsistent flyer metadata")
    return expected_pdf_key


def _find_r2_snapshot_for_ingestion(content_hash: str) -> str | None:
    try:
        return _find_r2_snapshot(content_hash)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchKey":
            raise
        logger.warning(
            "R2 snapshot listing returned NoSuchKey; proceeding without snapshot lookup "
            "for content_hash=%s",
            content_hash,
        )
        return None


def _persist_extraction(
    flyer_record: FlyerRecord,
    content_hash: str,
    pdf_bytes: bytes,
    acquisition_metadata: dict[str, Any],
) -> tuple[int, int, str]:
    cards = _extract_cards_from_pdf_bytes(pdf_bytes)
    cards_with_hash = []
    with tempfile.TemporaryDirectory(prefix="lidl-flyer-") as tmpdir:
        pdf_path = Path(tmpdir) / "flyer.pdf"
        pdf_path.write_bytes(pdf_bytes)
        for index, card in enumerate(cards):
            try:
                card_obj = type("C", (), card)()
                data, result = extract_card_image(pdf_path, card_obj, card_index=index + 1)
                if data is not None and flyer_record.id is not None and result.method != "none":
                    ext = "png" if result.content_type == "image/png" else "jpg"
                    image_key = object_key_for_card(flyer_record.id, index + 1, ext)
                    try:
                        r2.upload_object(image_key, data, result.content_type)
                    except Exception:
                        logger.exception("image upload failed flyer_id=%s card_index=%d", flyer_record.id, index + 1)
                    else:
                        card["image_object_key"] = image_key
                        card["image_content_type"] = result.content_type
                        card["image_width"] = result.width
                        card["image_height"] = result.height
                logger.info(
                    "card_image flyer_id=%s card_index=%d page=%s bbox=%s method=%s candidates=%d selected=%s reason=%s",
                    flyer_record.id,
                    index + 1,
                    card.get("page"),
                    card.get("bbox"),
                    result.method,
                    len(result.candidates),
                    result.selected_image,
                    result.reason,
                )
            except Exception:
                logger.exception("card image extraction failed flyer_id=%s card_index=%d", flyer_record.id, index + 1)
            cards_with_hash.append({**card, "card_hash": _card_hash(card)})

    extraction_key = r2.extraction_key_for_pdf_key(flyer_record.storage_key)
    payload = _flyer_snapshot_payload(
        flyer_record,
        acquisition_metadata,
        cards=cards_with_hash,
    )
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
    try:
        existing = db.get_flyer_by_hash(content_hash)
    except Exception:
        logger.exception("database lookup failed; persisting recovery data to R2")
        record = _new_flyer_record(flyer, storage_key, content_hash, downloaded_at)
        try:
            snapshot = _find_r2_snapshot_for_ingestion(content_hash)
            if snapshot is not None:
                record.storage_key = snapshot
                logger.info("R2 manifest already exists for content_hash=%s", content_hash)
            _ensure_pdf_in_r2(record.storage_key, content_hash, pdf_bytes)
            if snapshot is None:
                _upload_flyer_snapshot(record, flyer)
        except Exception:
            logger.exception("failed to persist R2 recovery data after database lookup failure")
            raise
        raise
    if existing is not None:
        logger.info("already ingested (hash match): %s", flyer.name)
        flyer_record = existing
        storage_key = flyer_record.storage_key
        slug_to_backfill = None
        if flyer_record.slug is None:
            # Legacy row ingested before slugs existed — backfill it now.
            slug_to_backfill = flyer_slug(
                flyer_record.category,
                flyer_record.name,
                flyer_record.start_date,
                content_hash,
            )
            flyer_record.slug = slug_to_backfill
        # If R2 object is somehow missing, re-upload it.
        pdf_already_exists = _ensure_pdf_in_r2(storage_key, content_hash, pdf_bytes)
        if not pdf_already_exists:
            logger.warning("DB record exists but R2 object missing — re-uploaded")
        _upload_flyer_snapshot(flyer_record, flyer)
        if slug_to_backfill is not None:
            db.update_flyer_slug(content_hash, slug_to_backfill)
        extracted_cards, persisted_cards, extraction_key = _persist_extraction(
            flyer_record, content_hash, pdf_bytes, flyer.to_dict()
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

    # --- Step 4: check R2 snapshot and upload the PDF if needed ---
    snapshot = _find_r2_snapshot_for_ingestion(content_hash)
    if snapshot is not None:
        storage_key = snapshot
        logger.info("R2 manifest already exists for content_hash=%s", content_hash)
    logger.info("uploading to R2: %s", storage_key)
    pdf_already_exists = _ensure_pdf_in_r2(storage_key, content_hash, pdf_bytes)

    # --- Step 5: insert DB record ---
    record = _new_flyer_record(flyer, storage_key, content_hash, downloaded_at)
    if snapshot is None:
        _upload_flyer_snapshot(record, flyer)
    flyer_record = db.insert_flyer(record)
    logger.info("ingested flyer: %s (id=%s)", flyer.name, flyer_record.id)
    extracted_cards, persisted_cards, extraction_key = _persist_extraction(
        flyer_record, content_hash, pdf_bytes, flyer.to_dict()
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
            except Exception as exc:
                logger.exception("failed to ingest flyer %s", flyer.name)
                results.append(
                    IngestionResult(
                        flyer_meta=flyer,
                        status=FlyerStatus.FAILED,
                        skipped=False,
                        storage_key="",
                        content_hash="",
                        error=str(exc),
                    )
                )
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
