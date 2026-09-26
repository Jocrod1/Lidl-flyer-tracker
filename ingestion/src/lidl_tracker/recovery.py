"""Rebuild PostgreSQL flyer and product-card data from R2 objects."""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import re
from typing import Any

from .ingest import _flyer_snapshot_payload, _persist_extraction
from .models.flyer import FlyerRecord, FlyerStatus
from .storage import database as db
from .storage import r2

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_SCHEMA_VERSION = 1


@dataclasses.dataclass(frozen=True)
class RecoveryResult:
    extraction_key: str
    content_hash: str
    name: str
    restored_flyer: bool
    card_count: int | None


@dataclasses.dataclass(frozen=True)
class SnapshotBackfillResult:
    extraction_key: str
    content_hash: str
    name: str
    written: bool


def _pdf_key_for_manifest(extraction_key: str) -> str:
    suffix = ".cards.json"
    if not extraction_key.endswith(suffix):
        raise ValueError(f"not an extraction manifest key: {extraction_key}")
    return f"{extraction_key[:-len(suffix)]}.pdf"


def _load_manifest(
    key: str,
    data: bytes,
    expected_pdf_key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        manifest = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON manifest {key}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError(f"manifest {key} must contain a JSON object")
    if manifest.get("schema_version") != _MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported or missing schema_version in {key}: "
            f"{manifest.get('schema_version')!r}"
        )

    flyer = manifest.get("flyer")
    if not isinstance(flyer, dict):
        raise ValueError(f"manifest {key} is missing flyer metadata")
    required = ("source_url", "storage_key", "category", "name", "content_hash", "status")
    missing = [field for field in required if field not in flyer or flyer[field] is None]
    if missing:
        raise ValueError(f"manifest {key} is missing required flyer fields: {', '.join(missing)}")
    invalid = [field for field in required if not isinstance(flyer[field], str)]
    if invalid:
        raise ValueError(f"manifest {key} has non-string flyer fields: {', '.join(invalid)}")
    if not flyer["source_url"] or not flyer["storage_key"] or not flyer["status"]:
        raise ValueError(f"manifest {key} has empty source_url, storage_key, or status")
    for field in ("start_date", "end_date", "slug", "downloaded_at"):
        if flyer.get(field) is not None and not isinstance(flyer[field], str):
            raise ValueError(f"manifest {key} has a non-string flyer.{field}")
    content_hash = flyer["content_hash"]
    if not isinstance(content_hash, str) or not _HASH_RE.fullmatch(content_hash):
        raise ValueError(f"manifest {key} has an invalid content_hash")
    if manifest.get("content_hash") != content_hash:
        raise ValueError(f"manifest {key} has inconsistent content_hash values")
    if flyer["storage_key"] != expected_pdf_key or manifest.get("pdf_storage_key") != expected_pdf_key:
        raise ValueError(f"manifest {key} does not reference its adjacent PDF {expected_pdf_key}")
    if not isinstance(manifest.get("acquisition"), dict):
        raise ValueError(f"manifest {key} is missing acquisition metadata")
    return manifest, flyer


def _record_from_snapshot(flyer: dict[str, Any]) -> FlyerRecord:
    downloaded_at = flyer.get("downloaded_at")
    if downloaded_at is not None:
        if not isinstance(downloaded_at, str):
            raise ValueError("flyer.downloaded_at must be an ISO-8601 string or null")
        try:
            downloaded_at = dt.datetime.fromisoformat(downloaded_at)
        except ValueError as exc:
            raise ValueError(f"invalid flyer.downloaded_at: {downloaded_at!r}") from exc

    try:
        status = FlyerStatus(flyer["status"])
    except ValueError as exc:
        raise ValueError(f"invalid flyer.status: {flyer['status']!r}") from exc

    return FlyerRecord(
        source_url=flyer["source_url"],
        storage_key=flyer["storage_key"],
        category=flyer["category"],
        name=flyer["name"],
        start_date=flyer.get("start_date"),
        end_date=flyer.get("end_date"),
        content_hash=flyer["content_hash"],
        downloaded_at=downloaded_at,
        status=status,
        slug=flyer.get("slug"),
    )


def restore_from_r2(*, dry_run: bool = False, prefix: str = "flyers/") -> list[RecoveryResult]:
    """Restore flyers and regenerate cards from every versioned R2 manifest.

    Existing flyer rows are left intact; their cards are refreshed from the
    source PDF. Running the operation again is safe.
    """
    results = []
    manifest_keys = sorted(key for key in r2.list_objects(prefix) if key.endswith(".cards.json"))
    for extraction_key in manifest_keys:
        pdf_key = _pdf_key_for_manifest(extraction_key)
        manifest, flyer_data = _load_manifest(
            extraction_key,
            r2.download_object(extraction_key),
            pdf_key,
        )
        pdf_bytes = r2.download_object(pdf_key)
        actual_hash = hashlib.sha256(pdf_bytes).hexdigest()
        if actual_hash != flyer_data["content_hash"]:
            raise ValueError(
                f"PDF hash mismatch for {pdf_key}: expected {flyer_data['content_hash']}, "
                f"got {actual_hash}"
            )

        record = _record_from_snapshot(flyer_data)
        existing = None if dry_run else db.get_flyer_by_hash(record.content_hash)
        restored_flyer = existing is None
        if existing is not None:
            record = existing
            if record.slug is None and flyer_data.get("slug"):
                db.update_flyer_slug(record.content_hash, flyer_data["slug"])
                record.slug = flyer_data["slug"]
        elif not dry_run:
            record = db.insert_flyer(record)

        card_count = None
        if not dry_run:
            card_count, _, _ = _persist_extraction(
                record,
                record.content_hash,
                pdf_bytes,
                manifest["acquisition"],
            )
        results.append(
            RecoveryResult(
                extraction_key=extraction_key,
                content_hash=record.content_hash,
                name=record.name,
                restored_flyer=restored_flyer,
                card_count=card_count,
            )
        )
    return results


def backfill_r2_manifests(
    *,
    dry_run: bool = False,
    page_size: int = 500,
) -> list[SnapshotBackfillResult]:
    """Upgrade existing R2 extraction objects with metadata from PostgreSQL."""
    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    results = []
    page = 1
    while True:
        flyers, total = db.list_flyers(page=page, page_size=page_size)
        for record, _ in flyers:
            if not r2.object_exists(record.storage_key):
                raise ValueError(f"R2 PDF is missing for flyer {record.content_hash}")
            pdf_bytes = r2.download_object(record.storage_key)
            actual_hash = hashlib.sha256(pdf_bytes).hexdigest()
            if actual_hash != record.content_hash:
                raise ValueError(
                    f"PDF hash mismatch for {record.storage_key}: expected "
                    f"{record.content_hash}, got {actual_hash}"
                )

            extraction_key = r2.extraction_key_for_pdf_key(record.storage_key)
            acquisition_metadata: dict[str, Any] = {"backfilled_from_database": True}
            cards: list[dict[str, Any]] = []
            if r2.object_exists(extraction_key):
                try:
                    existing = json.loads(r2.download_object(extraction_key).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid existing extraction JSON {extraction_key}: {exc}") from exc
                if not isinstance(existing, dict):
                    raise ValueError(f"existing extraction JSON {extraction_key} must be an object")
                existing_cards = existing.get("cards", [])
                if not isinstance(existing_cards, list):
                    raise ValueError(f"existing extraction JSON {extraction_key} has invalid cards")
                cards = existing_cards
                existing_acquisition = existing.get("acquisition")
                if isinstance(existing_acquisition, dict):
                    acquisition_metadata = existing_acquisition

            payload = _flyer_snapshot_payload(record, acquisition_metadata, cards=cards)
            if not dry_run:
                r2.upload_json(extraction_key, payload)
            results.append(
                SnapshotBackfillResult(
                    extraction_key=extraction_key,
                    content_hash=record.content_hash,
                    name=record.name,
                    written=not dry_run,
                )
            )

        if page * page_size >= total:
            break
        page += 1
    return results
