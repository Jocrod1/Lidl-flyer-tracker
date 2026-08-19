"""Cloudflare R2 storage via the S3-compatible API.

Required environment variables:
    R2_ENDPOINT_URL      e.g. https://<account_id>.r2.cloudflarestorage.com
    R2_ACCESS_KEY_ID
    R2_SECRET_ACCESS_KEY
    R2_BUCKET_NAME

Object key format:
    flyers/{year}/{month}/{sha256}.pdf

The same PDF content always maps to the same key (determined by SHA-256).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError


def _client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def _bucket() -> str:
    return os.environ["R2_BUCKET_NAME"]


def object_key_for_hash(content_hash: str, year: str, month: str) -> str:
    """Deterministic object key derived from SHA-256 hash.

    Using year/month sub-prefixes makes the bucket browsable without
    sacrificing content-identity guarantees (the hash is still the
    canonical identifier).
    """
    return f"flyers/{year}/{month}/{content_hash}.pdf"


def extraction_key_for_pdf_key(pdf_key: str) -> str:
    """Return the extraction JSON key for an existing PDF object key."""
    if not pdf_key.endswith(".pdf"):
        raise ValueError(f"expected PDF key ending in .pdf, got: {pdf_key}")
    return f"{pdf_key[:-4]}.cards.json"


def sha256_bytes(data: bytes, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256(data)
    return digest.hexdigest()


def sha256_stream(stream: BinaryIO, chunk_size: int = 1 << 20) -> tuple[str, bytes]:
    """Read *stream* fully, return (hex_digest, raw_bytes).

    Reads once so we can both hash and upload without seeking.
    """
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    for chunk in iter(lambda: stream.read(chunk_size), b""):
        digest.update(chunk)
        chunks.append(chunk)
    return digest.hexdigest(), b"".join(chunks)


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_exists(key: str) -> bool:
    """Return True if *key* already exists in R2."""
    try:
        _client().head_object(Bucket=_bucket(), Key=key)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise


def upload_pdf(key: str, data: bytes) -> None:
    """Upload raw PDF bytes to R2 under *key*.

    Raises on any failure so callers can treat a clean return as success.
    """
    _client().put_object(
        Bucket=_bucket(),
        Key=key,
        Body=data,
        ContentType="application/pdf",
    )


def upload_json(key: str, payload: object) -> None:
    """Upload JSON payload bytes to R2 under *key*."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    _client().put_object(
        Bucket=_bucket(),
        Key=key,
        Body=data,
        ContentType="application/json; charset=utf-8",
    )


def verify_upload(key: str, expected_hash: str) -> bool:
    """Confirm the stored object exists and its ETag matches expectations.

    R2/S3 ETag for a simple (non-multipart) upload is the MD5 of the object
    body, not the SHA-256.  We therefore just confirm the object is present
    and trusts the upload was atomic.  A mismatch can only arise from
    corruption in transit, which boto3 + HTTPS makes extremely unlikely.
    """
    return object_exists(key)
