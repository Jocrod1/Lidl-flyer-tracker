from __future__ import annotations

import hashlib
import json
from unittest.mock import patch

import pytest

from lidl_tracker.models.flyer import FlyerRecord, FlyerStatus
from lidl_tracker.recovery import backfill_r2_manifests, restore_from_r2

PDF_BYTES = b"%PDF-1.4 recovery fixture"
CONTENT_HASH = hashlib.sha256(PDF_BYTES).hexdigest()
PDF_KEY = f"flyers/2025/07/{CONTENT_HASH}.pdf"
MANIFEST_KEY = f"flyers/2025/07/{CONTENT_HASH}.cards.json"


def _manifest(**flyer_overrides):
    flyer = {
        "source_url": "https://example.com/flyer.pdf",
        "storage_key": PDF_KEY,
        "category": "Weekly",
        "name": "Weekly flyer",
        "start_date": "2025-07-14",
        "end_date": "2025-07-20",
        "content_hash": CONTENT_HASH,
        "downloaded_at": "2025-07-14T10:00:00+00:00",
        "status": "STORED",
        "slug": "weekly-flyer",
    }
    flyer.update(flyer_overrides)
    return {
        "schema_version": 1,
        "flyer": flyer,
        "acquisition": {"id": "source-flyer-id", "slug": "weekly"},
        "flyer_id": 999,
        "content_hash": CONTENT_HASH,
        "pdf_storage_key": PDF_KEY,
        "card_count": 1,
        "cards": [{"page": 999, "bbox": [0, 0, 1, 1]}],
    }


def _mock_r2(monkeypatch, manifest=None, pdf=PDF_BYTES):
    manifest_bytes = json.dumps(manifest or _manifest()).encode()
    objects = {MANIFEST_KEY: manifest_bytes, PDF_KEY: pdf}
    monkeypatch.setattr("lidl_tracker.recovery.r2.list_objects", lambda prefix: iter([MANIFEST_KEY]))
    monkeypatch.setattr("lidl_tracker.recovery.r2.download_object", lambda key: objects[key])


def _insert_with_id(record):
    record.id = 1
    return record


def test_dry_run_validates_manifest_and_pdf_without_database_writes(monkeypatch):
    _mock_r2(monkeypatch)
    with (
        patch("lidl_tracker.recovery.db.get_flyer_by_hash") as get_flyer,
        patch("lidl_tracker.recovery.db.insert_flyer") as insert_flyer,
        patch("lidl_tracker.recovery._persist_extraction") as persist,
    ):
        results = restore_from_r2(dry_run=True)

    assert len(results) == 1
    assert results[0].restored_flyer is True
    assert results[0].card_count is None
    get_flyer.assert_not_called()
    insert_flyer.assert_not_called()
    persist.assert_not_called()


def test_restore_inserts_metadata_and_regenerates_cards(monkeypatch):
    _mock_r2(monkeypatch)
    with (
        patch("lidl_tracker.recovery.db.get_flyer_by_hash", return_value=None),
        patch("lidl_tracker.recovery.db.insert_flyer", side_effect=_insert_with_id) as insert,
        patch("lidl_tracker.recovery._persist_extraction", return_value=(3, 3, MANIFEST_KEY)) as persist,
    ):
        results = restore_from_r2()

    record = insert.call_args.args[0]
    assert record.source_url == "https://example.com/flyer.pdf"
    assert record.storage_key == PDF_KEY
    assert record.category == "Weekly"
    assert record.slug == "weekly-flyer"
    assert record.status == FlyerStatus.STORED
    assert record.downloaded_at.isoformat() == "2025-07-14T10:00:00+00:00"
    assert record.id == 1
    persist.assert_called_once_with(
        record,
        CONTENT_HASH,
        PDF_BYTES,
        {"id": "source-flyer-id", "slug": "weekly"},
    )
    assert results[0].restored_flyer is True
    assert results[0].card_count == 3


def test_existing_flyer_is_not_inserted_again_but_cards_are_refreshed(monkeypatch):
    _mock_r2(monkeypatch)
    existing = FlyerRecord(
        id=8,
        source_url="https://example.com/flyer.pdf",
        storage_key=PDF_KEY,
        category="Weekly",
        name="Weekly flyer",
        start_date="2025-07-14",
        end_date="2025-07-20",
        content_hash=CONTENT_HASH,
        status=FlyerStatus.STORED,
    )
    with (
        patch("lidl_tracker.recovery.db.get_flyer_by_hash", return_value=existing),
        patch("lidl_tracker.recovery.db.insert_flyer") as insert,
        patch("lidl_tracker.recovery.db.update_flyer_slug") as update_slug,
        patch("lidl_tracker.recovery._persist_extraction", return_value=(2, 2, MANIFEST_KEY)) as persist,
    ):
        results = restore_from_r2()

    insert.assert_not_called()
    update_slug.assert_called_once_with(CONTENT_HASH, "weekly-flyer")
    persist.assert_called_once()
    assert results[0].restored_flyer is False


def test_pdf_hash_mismatch_stops_restore_before_database_write(monkeypatch):
    _mock_r2(monkeypatch, pdf=b"not the stored PDF")
    with (
        patch("lidl_tracker.recovery.db.get_flyer_by_hash") as get_flyer,
        pytest.raises(ValueError, match="PDF hash mismatch"),
    ):
        restore_from_r2()
    get_flyer.assert_not_called()


def test_legacy_manifest_without_schema_is_reported(monkeypatch):
    _mock_r2(monkeypatch, manifest={"content_hash": CONTENT_HASH})
    with pytest.raises(ValueError, match="unsupported or missing schema_version"):
        restore_from_r2(dry_run=True)


def test_manifest_cannot_point_at_a_different_pdf(monkeypatch):
    _mock_r2(monkeypatch, manifest=_manifest(storage_key="flyers/other.pdf"))
    with pytest.raises(ValueError, match="does not reference its adjacent PDF"):
        restore_from_r2(dry_run=True)


def test_backfill_adds_database_metadata_and_preserves_existing_cards(monkeypatch):
    record = FlyerRecord(
        id=7,
        source_url="https://example.com/flyer.pdf",
        storage_key=PDF_KEY,
        category="Weekly",
        name="Weekly flyer",
        start_date="2025-07-14",
        end_date="2025-07-20",
        content_hash=CONTENT_HASH,
        status=FlyerStatus.STORED,
        slug="weekly-flyer",
    )
    old_cards = [{"page": 4, "bbox": [1, 2, 3, 4], "name": "Product"}]
    old_json = json.dumps({"flyer_id": 7, "card_count": 1, "cards": old_cards}).encode()
    monkeypatch.setattr("lidl_tracker.recovery.db.list_flyers", lambda **_: ([(record, 1)], 1))
    monkeypatch.setattr(
        "lidl_tracker.recovery.r2.object_exists",
        lambda key: key in (PDF_KEY, MANIFEST_KEY),
    )
    monkeypatch.setattr(
        "lidl_tracker.recovery.r2.download_object",
        lambda key: old_json if key == MANIFEST_KEY else PDF_BYTES,
    )
    with patch("lidl_tracker.recovery.r2.upload_json") as upload:
        results = backfill_r2_manifests()

    key, payload = upload.call_args.args
    assert key == MANIFEST_KEY
    assert payload["schema_version"] == 1
    assert payload["flyer"]["source_url"] == record.source_url
    assert payload["flyer"]["slug"] == record.slug
    assert payload["cards"] == old_cards
    assert payload["acquisition"] == {"backfilled_from_database": True}
    assert results[0].written is True


def test_backfill_dry_run_does_not_write_snapshots(monkeypatch):
    record = FlyerRecord(
        id=7,
        source_url="https://example.com/flyer.pdf",
        storage_key=PDF_KEY,
        category="Weekly",
        name="Weekly flyer",
        content_hash=CONTENT_HASH,
        status=FlyerStatus.STORED,
    )
    monkeypatch.setattr("lidl_tracker.recovery.db.list_flyers", lambda **_: ([(record, 0)], 1))
    monkeypatch.setattr(
        "lidl_tracker.recovery.r2.object_exists",
        lambda key: key == PDF_KEY,
    )
    monkeypatch.setattr("lidl_tracker.recovery.r2.download_object", lambda key: PDF_BYTES)
    with patch("lidl_tracker.recovery.r2.upload_json") as upload:
        results = backfill_r2_manifests(dry_run=True)

    upload.assert_not_called()
    assert results[0].written is False


def test_backfill_rejects_pdf_hash_mismatch(monkeypatch):
    record = FlyerRecord(
        id=7,
        source_url="https://example.com/flyer.pdf",
        storage_key=PDF_KEY,
        category="Weekly",
        name="Weekly flyer",
        content_hash=CONTENT_HASH,
        status=FlyerStatus.STORED,
    )
    monkeypatch.setattr("lidl_tracker.recovery.db.list_flyers", lambda **_: ([(record, 0)], 1))
    monkeypatch.setattr("lidl_tracker.recovery.r2.object_exists", lambda key: True)
    monkeypatch.setattr("lidl_tracker.recovery.r2.download_object", lambda key: b"wrong pdf")
    with patch("lidl_tracker.recovery.r2.upload_json") as upload:
        with pytest.raises(ValueError, match="PDF hash mismatch"):
            backfill_r2_manifests()

    upload.assert_not_called()
