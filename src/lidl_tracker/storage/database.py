"""PostgreSQL persistence layer for flyer metadata.

Required environment variable:
    DATABASE_URL   e.g. postgresql://user:pass@host:5432/dbname

Uses psycopg2 directly to keep dependencies minimal and match the
project's dependency-light philosophy.
"""

from __future__ import annotations

import datetime as dt
import os
from contextlib import contextmanager
from typing import Generator, Optional

import psycopg2
import psycopg2.extras

from ..models.flyer import FlyerRecord, FlyerStatus


def _connect():
    return psycopg2.connect(os.environ["DATABASE_URL"])


@contextmanager
def _cursor() -> Generator:
    conn = _connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


def apply_migrations(conn=None) -> None:
    """Create the flyers table if it does not exist.

    Idempotent — safe to call on every startup.
    """
    sql = """
    CREATE TABLE IF NOT EXISTS flyers (
        id             SERIAL PRIMARY KEY,
        source_url     TEXT        NOT NULL,
        storage_key    TEXT        NOT NULL,
        category       TEXT        NOT NULL DEFAULT '',
        name           TEXT        NOT NULL DEFAULT '',
        start_date     TEXT,
        end_date       TEXT,
        content_hash   TEXT        NOT NULL,
        downloaded_at  TIMESTAMPTZ,
        created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        status         TEXT        NOT NULL DEFAULT 'DISCOVERED',
        CONSTRAINT flyers_content_hash_unique UNIQUE (content_hash),
        CONSTRAINT flyers_source_url_unique   UNIQUE (source_url)
    );
    CREATE INDEX IF NOT EXISTS flyers_status_idx ON flyers (status);
    """
    if conn is not None:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    else:
        with _cursor() as cur:
            cur.execute(sql)


def get_flyer_by_hash(content_hash: str) -> Optional[FlyerRecord]:
    """Return the FlyerRecord for *content_hash*, or None if not found."""
    with _cursor() as cur:
        cur.execute("SELECT * FROM flyers WHERE content_hash = %s", (content_hash,))
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def get_flyer_by_url(source_url: str) -> Optional[FlyerRecord]:
    """Return the FlyerRecord for *source_url*, or None if not found."""
    with _cursor() as cur:
        cur.execute("SELECT * FROM flyers WHERE source_url = %s", (source_url,))
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def insert_flyer(record: FlyerRecord) -> FlyerRecord:
    """Insert *record* and return it with id and created_at populated.

    Raises psycopg2.errors.UniqueViolation if content_hash or source_url
    already exists (callers should check first via get_flyer_by_hash).
    """
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO flyers
                (source_url, storage_key, category, name,
                 start_date, end_date, content_hash,
                 downloaded_at, status)
            VALUES
                (%(source_url)s, %(storage_key)s, %(category)s, %(name)s,
                 %(start_date)s, %(end_date)s, %(content_hash)s,
                 %(downloaded_at)s, %(status)s)
            RETURNING id, created_at
            """,
            {
                "source_url": record.source_url,
                "storage_key": record.storage_key,
                "category": record.category,
                "name": record.name,
                "start_date": record.start_date,
                "end_date": record.end_date,
                "content_hash": record.content_hash,
                "downloaded_at": record.downloaded_at,
                "status": record.status.value,
            },
        )
        row = cur.fetchone()
    record.id = row["id"]
    record.created_at = row["created_at"]
    return record


def update_flyer_status(content_hash: str, status: FlyerStatus) -> None:
    """Update the status column for the row identified by *content_hash*."""
    with _cursor() as cur:
        cur.execute(
            "UPDATE flyers SET status = %s WHERE content_hash = %s",
            (status.value, content_hash),
        )


def _row_to_record(row: dict) -> FlyerRecord:
    return FlyerRecord(
        id=row["id"],
        source_url=row["source_url"],
        storage_key=row["storage_key"],
        category=row["category"],
        name=row["name"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        content_hash=row["content_hash"],
        downloaded_at=row["downloaded_at"],
        created_at=row["created_at"],
        status=FlyerStatus(row["status"]),
    )
