"""Unit tests for R2 storage helpers.

No real Cloudflare credentials required — boto3 calls are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lidl_tracker.storage.r2 import (
    object_key_for_hash,
    object_exists,
    sha256_bytes,
    sha256_file,
    upload_pdf,
    verify_upload,
)


# ---------------------------------------------------------------------------
# SHA-256 helpers
# ---------------------------------------------------------------------------

class TestSha256:
    def test_known_hash(self):
        # echo -n "hello" | sha256sum
        assert sha256_bytes(b"hello") == (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )

    def test_empty_bytes(self):
        assert sha256_bytes(b"") == (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_sha256_file(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"hello")
        assert sha256_file(f) == sha256_bytes(b"hello")


# ---------------------------------------------------------------------------
# Deterministic object key
# ---------------------------------------------------------------------------

class TestObjectKey:
    def test_key_structure(self):
        key = object_key_for_hash("abc123", "2025", "07")
        assert key == "flyers/2025/07/abc123.pdf"

    def test_same_hash_same_key(self):
        h = "deadbeef" * 8
        k1 = object_key_for_hash(h, "2025", "07")
        k2 = object_key_for_hash(h, "2025", "07")
        assert k1 == k2

    def test_different_hash_different_key(self):
        k1 = object_key_for_hash("aaa", "2025", "07")
        k2 = object_key_for_hash("bbb", "2025", "07")
        assert k1 != k2


# ---------------------------------------------------------------------------
# object_exists — mocked boto3
# ---------------------------------------------------------------------------

R2_ENV = {
    "R2_ENDPOINT_URL": "https://fake.r2.cloudflarestorage.com",
    "R2_ACCESS_KEY_ID": "FAKEID",
    "R2_SECRET_ACCESS_KEY": "FAKESECRET",
    "R2_BUCKET_NAME": "test-bucket",
}


class TestObjectExists:
    def test_returns_true_when_object_present(self, monkeypatch):
        monkeypatch.setenv("R2_ENDPOINT_URL", R2_ENV["R2_ENDPOINT_URL"])
        monkeypatch.setenv("R2_ACCESS_KEY_ID", R2_ENV["R2_ACCESS_KEY_ID"])
        monkeypatch.setenv("R2_SECRET_ACCESS_KEY", R2_ENV["R2_SECRET_ACCESS_KEY"])
        monkeypatch.setenv("R2_BUCKET_NAME", R2_ENV["R2_BUCKET_NAME"])

        mock_client = MagicMock()
        mock_client.head_object.return_value = {}
        with patch("lidl_tracker.storage.r2._client", return_value=mock_client):
            assert object_exists("flyers/2025/07/abc.pdf") is True

    def test_returns_false_on_404(self, monkeypatch):
        from botocore.exceptions import ClientError

        monkeypatch.setenv("R2_ENDPOINT_URL", R2_ENV["R2_ENDPOINT_URL"])
        monkeypatch.setenv("R2_ACCESS_KEY_ID", R2_ENV["R2_ACCESS_KEY_ID"])
        monkeypatch.setenv("R2_SECRET_ACCESS_KEY", R2_ENV["R2_SECRET_ACCESS_KEY"])
        monkeypatch.setenv("R2_BUCKET_NAME", R2_ENV["R2_BUCKET_NAME"])

        error = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        mock_client = MagicMock()
        mock_client.head_object.side_effect = error
        with patch("lidl_tracker.storage.r2._client", return_value=mock_client):
            assert object_exists("flyers/2025/07/missing.pdf") is False


# ---------------------------------------------------------------------------
# upload_pdf — mocked boto3
# ---------------------------------------------------------------------------

class TestUploadPdf:
    def test_upload_calls_put_object(self, monkeypatch):
        monkeypatch.setenv("R2_ENDPOINT_URL", R2_ENV["R2_ENDPOINT_URL"])
        monkeypatch.setenv("R2_ACCESS_KEY_ID", R2_ENV["R2_ACCESS_KEY_ID"])
        monkeypatch.setenv("R2_SECRET_ACCESS_KEY", R2_ENV["R2_SECRET_ACCESS_KEY"])
        monkeypatch.setenv("R2_BUCKET_NAME", R2_ENV["R2_BUCKET_NAME"])

        mock_client = MagicMock()
        mock_client.put_object.return_value = {}
        with patch("lidl_tracker.storage.r2._client", return_value=mock_client):
            upload_pdf("flyers/2025/07/abc.pdf", b"%PDF-fake")

        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="flyers/2025/07/abc.pdf",
            Body=b"%PDF-fake",
            ContentType="application/pdf",
        )

    def test_upload_failure_propagates(self, monkeypatch):
        from botocore.exceptions import ClientError

        monkeypatch.setenv("R2_ENDPOINT_URL", R2_ENV["R2_ENDPOINT_URL"])
        monkeypatch.setenv("R2_ACCESS_KEY_ID", R2_ENV["R2_ACCESS_KEY_ID"])
        monkeypatch.setenv("R2_SECRET_ACCESS_KEY", R2_ENV["R2_SECRET_ACCESS_KEY"])
        monkeypatch.setenv("R2_BUCKET_NAME", R2_ENV["R2_BUCKET_NAME"])

        error = ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "PutObject")
        mock_client = MagicMock()
        mock_client.put_object.side_effect = error
        with patch("lidl_tracker.storage.r2._client", return_value=mock_client):
            with pytest.raises(ClientError):
                upload_pdf("flyers/2025/07/abc.pdf", b"%PDF-fake")
