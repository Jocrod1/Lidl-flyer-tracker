"""Integration tests for the PostgreSQL persistence layer.

These exercise real SQL against a real Postgres instance (the one
provided by `docker compose up -d postgres`, matching `.env.example`).
They are skipped automatically when no reachable database is configured,
so `pytest ingestion/tests` still passes in environments without Docker
— but they are real coverage, not mocks, when run locally or in CI with
compose up.
"""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest

from lidl_tracker.models.flyer import FlyerRecord, FlyerStatus
from lidl_tracker.storage import database as db

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://lidl:lidl@localhost:5432/lidl_dev"),
)


def _database_available() -> bool:
    try:
        conn = psycopg2.connect(TEST_DATABASE_URL, connect_timeout=2)
    except Exception:
        return False
    conn.close()
    return True


pytestmark = pytest.mark.skipif(
    not _database_available(),
    reason="no reachable PostgreSQL instance (start it with `docker compose up -d postgres`)",
)


@pytest.fixture(autouse=True)
def _use_test_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    db.apply_migrations()
    yield
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE flyers RESTART IDENTITY CASCADE")
        conn.commit()


def _insert_flyer(**overrides) -> FlyerRecord:
    defaults = dict(
        source_url=f"https://example.com/{uuid.uuid4()}.pdf",
        storage_key=f"flyers/2026/08/{uuid.uuid4()}.pdf",
        category="ALIMENTACION",
        name="Folleto Semanal",
        content_hash=uuid.uuid4().hex,
        status=FlyerStatus.STORED,
        start_date="2026-08-17",
        end_date="2026-08-23",
        slug=None,
    )
    defaults.update(overrides)
    return db.insert_flyer(FlyerRecord(**defaults))


def _card(suffix: str) -> dict:
    return {
        "page": 1,
        "bbox": [0, 0, 1, 1],
        "brand": "TEST",
        "name": f"Product {suffix}",
        "description": "",
        "quantity": {"value": 1.0, "unit": "kg", "raw": "1 kg"},
        "price": 1.0,
        "reference_price": None,
        "unit_prices": [],
        "discount_percent": None,
        "lidl_plus": False,
        "currency": "EUR",
        "status": "ok",
        "warnings": [],
        "notes": [],
        "raw_text": f"TEST\nProduct {suffix}",
        "parser_version": "0.1.0",
        "card_hash": f"hash-{suffix}-{uuid.uuid4().hex}",
    }


class TestSlugBackfill:
    def test_backfill_populates_null_slugs(self):
        record = _insert_flyer(slug=None)
        assert record.slug is None

        updated = db.backfill_flyer_slugs()

        assert updated == 1
        refreshed = db.get_flyer_by_hash(record.content_hash)
        assert refreshed.slug is not None
        assert refreshed.slug.startswith("alimentacion-folleto-semanal-2026-08-17-")

    def test_backfill_is_idempotent(self):
        _insert_flyer(slug=None)
        first = db.backfill_flyer_slugs()
        second = db.backfill_flyer_slugs()
        assert first == 1
        assert second == 0

    def test_update_flyer_slug_only_sets_when_null(self):
        record = _insert_flyer(slug=None)
        db.update_flyer_slug(record.content_hash, "custom-slug")
        db.update_flyer_slug(record.content_hash, "should-not-apply")

        refreshed = db.get_flyer_by_hash(record.content_hash)
        assert refreshed.slug == "custom-slug"


class TestListFlyers:
    def test_returns_most_recent_first_with_product_count(self):
        older = _insert_flyer(start_date="2026-08-10", slug="older-flyer")
        newer = _insert_flyer(start_date="2026-08-17", slug="newer-flyer")
        db.upsert_product_cards(newer.id, [_card("a"), _card("b")])
        db.upsert_product_cards(older.id, [_card("c")])

        items, total = db.list_flyers(page=1, page_size=10)

        assert total == 2
        assert [record.slug for record, _ in items] == ["newer-flyer", "older-flyer"]
        counts = {record.slug: count for record, count in items}
        assert counts["newer-flyer"] == 2
        assert counts["older-flyer"] == 1

    def test_year_filter(self):
        _insert_flyer(start_date="2025-12-01", slug="last-year")
        _insert_flyer(start_date="2026-01-05", slug="this-year")

        items, total = db.list_flyers(year=2026, page=1, page_size=10)

        assert total == 1
        assert items[0][0].slug == "this-year"

    def test_pagination(self):
        for i in range(3):
            _insert_flyer(start_date=f"2026-08-{10 + i:02d}", slug=f"flyer-{i}")

        page1, total = db.list_flyers(page=1, page_size=2)
        page2, _ = db.list_flyers(page=2, page_size=2)

        assert total == 3
        assert len(page1) == 2
        assert len(page2) == 1


class TestGetFlyerBySlug:
    def test_found_returns_record_and_product_count(self):
        record = _insert_flyer(slug="a-flyer")
        db.upsert_product_cards(record.id, [_card("a"), _card("b")])

        result = db.get_flyer_by_slug("a-flyer")

        assert result is not None
        found_record, count = result
        assert found_record.id == record.id
        assert count == 2

    def test_not_found_returns_none(self):
        assert db.get_flyer_by_slug("does-not-exist") is None
