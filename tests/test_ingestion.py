"""Unit tests for the flyer ingestion pipeline.

No real network, R2, or database calls — everything is mocked.
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

import pytest

from lidl_tracker.acquisition import FlyerMeta
from lidl_tracker.ingest import ingest_flyer, IngestionResult
from lidl_tracker.models.flyer import FlyerRecord, FlyerStatus
from lidl_tracker.storage.r2 import sha256_bytes, object_key_for_hash


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

PDF_BYTES = b"%PDF-1.4 fake content"
PDF_HASH = sha256_bytes(PDF_BYTES)
NOW = dt.datetime(2025, 7, 14, 10, 0, 0, tzinfo=dt.timezone.utc)
STORAGE_KEY = object_key_for_hash(PDF_HASH, "2025", "07")


def _make_flyer(**kwargs) -> FlyerMeta:
    defaults = dict(
        id="flyer-001",
        slug="folleto-001",
        name="Folleto Semanal",
        title="Folleto Semanal",
        category="Folletos",
        subcategory="General",
        pdf_url="https://assets.leaflets.schwarz/fake/flyer.pdf",
        flyer_url="https://lidl.es/l/folletos/folleto-001/",
        start_date="2025-07-14",
        end_date="2025-07-20",
        offer_start_date="2025-07-14",
        offer_end_date="2025-07-20",
        status="active",
        file_size=len(PDF_BYTES),
        discovered_at="2025-07-14T10:00:00+00:00",
    )
    defaults.update(kwargs)
    return FlyerMeta(**defaults)


def _make_existing_record() -> FlyerRecord:
    return FlyerRecord(
        id=1,
        source_url="https://assets.leaflets.schwarz/fake/flyer.pdf",
        storage_key=STORAGE_KEY,
        category="Folletos",
        name="Folleto Semanal",
        start_date="2025-07-14",
        end_date="2025-07-20",
        content_hash=PDF_HASH,
        downloaded_at=NOW,
        created_at=NOW,
        status=FlyerStatus.STORED,
    )


# ---------------------------------------------------------------------------
# Ingestion: new flyer
# ---------------------------------------------------------------------------

class TestIngestNewFlyer:
    def test_new_flyer_uploads_and_inserts(self, monkeypatch):
        flyer = _make_flyer()
        mock_client = MagicMock()
        mock_client._client.stream.return_value.__enter__.return_value.read.return_value = PDF_BYTES

        with (
            patch("lidl_tracker.ingest.db.get_flyer_by_hash", return_value=None),
            patch("lidl_tracker.ingest.r2.upload_pdf") as mock_upload,
            patch("lidl_tracker.ingest.r2.verify_upload", return_value=True),
            patch("lidl_tracker.ingest.db.insert_flyer", side_effect=lambda r: r) as mock_insert,
        ):
            result = ingest_flyer(flyer, mock_client, now=NOW)

        assert result.skipped is False
        assert result.status == FlyerStatus.STORED
        assert result.content_hash == PDF_HASH
        assert result.storage_key == STORAGE_KEY
        mock_upload.assert_called_once_with(STORAGE_KEY, PDF_BYTES)
        mock_insert.assert_called_once()

    def test_new_flyer_uses_deterministic_key(self, monkeypatch):
        """The same PDF bytes always produce the same storage key."""
        flyer1 = _make_flyer(pdf_url="https://example.com/a.pdf")
        flyer2 = _make_flyer(pdf_url="https://example.com/b.pdf")

        mock_client = MagicMock()
        mock_client._client.stream.return_value.__enter__.return_value.read.return_value = PDF_BYTES

        keys = []

        def capture_upload(key, data):
            keys.append(key)

        with (
            patch("lidl_tracker.ingest.db.get_flyer_by_hash", return_value=None),
            patch("lidl_tracker.ingest.r2.upload_pdf", side_effect=capture_upload),
            patch("lidl_tracker.ingest.r2.verify_upload", return_value=True),
            patch("lidl_tracker.ingest.db.insert_flyer", side_effect=lambda r: r),
        ):
            ingest_flyer(flyer1, mock_client, now=NOW)
            ingest_flyer(flyer2, mock_client, now=NOW)

        assert keys[0] == keys[1], "Same PDF content must produce the same storage key"


# ---------------------------------------------------------------------------
# Idempotency: duplicate flyer
# ---------------------------------------------------------------------------

class TestDuplicateFlyer:
    def test_duplicate_hash_is_skipped(self):
        """Re-ingesting the same PDF content returns skipped=True, no upload."""
        flyer = _make_flyer()
        mock_client = MagicMock()
        mock_client._client.stream.return_value.__enter__.return_value.read.return_value = PDF_BYTES
        existing = _make_existing_record()

        with (
            patch("lidl_tracker.ingest.db.get_flyer_by_hash", return_value=existing),
            patch("lidl_tracker.ingest.r2.object_exists", return_value=True),
            patch("lidl_tracker.ingest.r2.upload_pdf") as mock_upload,
            patch("lidl_tracker.ingest.db.insert_flyer") as mock_insert,
        ):
            result = ingest_flyer(flyer, mock_client, now=NOW)

        assert result.skipped is True
        mock_upload.assert_not_called()
        mock_insert.assert_not_called()

    def test_duplicate_hash_reupload_if_r2_missing(self):
        """If DB record exists but R2 object is gone, re-upload without DB insert."""
        flyer = _make_flyer()
        mock_client = MagicMock()
        mock_client._client.stream.return_value.__enter__.return_value.read.return_value = PDF_BYTES
        existing = _make_existing_record()

        with (
            patch("lidl_tracker.ingest.db.get_flyer_by_hash", return_value=existing),
            patch("lidl_tracker.ingest.r2.object_exists", return_value=False),
            patch("lidl_tracker.ingest.r2.upload_pdf") as mock_upload,
            patch("lidl_tracker.ingest.db.insert_flyer") as mock_insert,
        ):
            result = ingest_flyer(flyer, mock_client, now=NOW)

        assert result.skipped is True
        mock_upload.assert_called_once_with(STORAGE_KEY, PDF_BYTES)
        mock_insert.assert_not_called()


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

class TestFailureHandling:
    def test_r2_upload_failure_propagates(self):
        flyer = _make_flyer()
        mock_client = MagicMock()
        mock_client._client.stream.return_value.__enter__.return_value.read.return_value = PDF_BYTES

        with (
            patch("lidl_tracker.ingest.db.get_flyer_by_hash", return_value=None),
            patch("lidl_tracker.ingest.r2.upload_pdf", side_effect=RuntimeError("R2 down")),
        ):
            with pytest.raises(RuntimeError, match="R2 down"):
                ingest_flyer(flyer, mock_client, now=NOW)

    def test_db_insert_failure_propagates(self):
        flyer = _make_flyer()
        mock_client = MagicMock()
        mock_client._client.stream.return_value.__enter__.return_value.read.return_value = PDF_BYTES

        with (
            patch("lidl_tracker.ingest.db.get_flyer_by_hash", return_value=None),
            patch("lidl_tracker.ingest.r2.upload_pdf"),
            patch("lidl_tracker.ingest.r2.verify_upload", return_value=True),
            patch("lidl_tracker.ingest.db.insert_flyer", side_effect=Exception("DB down")),
        ):
            with pytest.raises(Exception, match="DB down"):
                ingest_flyer(flyer, mock_client, now=NOW)

    def test_retry_after_db_failure_does_not_duplicate_r2(self):
        """On retry after a DB failure, R2 upload is still called (idempotent overwrite),
        but a new DB record is inserted only once."""
        flyer = _make_flyer()
        mock_client = MagicMock()
        mock_client._client.stream.return_value.__enter__.return_value.read.return_value = PDF_BYTES

        upload_calls = []

        def record_upload(key, data):
            upload_calls.append(key)

        # First attempt: upload ok, DB fails
        with (
            patch("lidl_tracker.ingest.db.get_flyer_by_hash", return_value=None),
            patch("lidl_tracker.ingest.r2.upload_pdf", side_effect=record_upload),
            patch("lidl_tracker.ingest.r2.verify_upload", return_value=True),
            patch("lidl_tracker.ingest.db.insert_flyer", side_effect=Exception("DB down")),
        ):
            with pytest.raises(Exception, match="DB down"):
                ingest_flyer(flyer, mock_client, now=NOW)

        assert len(upload_calls) == 1

        # Second attempt: DB now works, R2 overwrites same key (still 1 new key call)
        with (
            patch("lidl_tracker.ingest.db.get_flyer_by_hash", return_value=None),
            patch("lidl_tracker.ingest.r2.upload_pdf", side_effect=record_upload),
            patch("lidl_tracker.ingest.r2.verify_upload", return_value=True),
            patch("lidl_tracker.ingest.db.insert_flyer", side_effect=lambda r: r),
        ):
            result = ingest_flyer(flyer, mock_client, now=NOW)

        assert result.skipped is False
        assert len(upload_calls) == 2
        # Both calls used the same deterministic key
        assert upload_calls[0] == upload_calls[1]
