"""Integration tests for the PostgreSQL persistence layer.

These exercise real SQL against a real Postgres instance. Set
`TEST_DATABASE_URL` explicitly to choose the test server.
They are skipped automatically when no reachable database is configured,
so `pytest ingestion/tests` still passes in environments without Docker
— but they are real coverage, not mocks, when a test server is available.
"""

from __future__ import annotations

import os
import uuid
from contextlib import closing

import psycopg2
import pytest

from lidl_tracker.models.flyer import FlyerRecord, FlyerStatus
from lidl_tracker.storage import database as db

# Do not inherit DATABASE_URL: database tests must use an explicit test target.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://localhost:5432/lidl_test",
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
    reason="no reachable PostgreSQL test instance (set TEST_DATABASE_URL)",
)


@pytest.fixture(autouse=True)
def _use_test_database(monkeypatch):
    schema = f"test_lidl_{uuid.uuid4().hex}"
    with closing(psycopg2.connect(TEST_DATABASE_URL)) as conn, conn:
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {schema}")

    def connect_to_isolated_schema():
        return psycopg2.connect(
            TEST_DATABASE_URL,
            options=f"-c search_path={schema}",
        )

    monkeypatch.setattr(db, "_connect", connect_to_isolated_schema)
    try:
        db.apply_migrations()
        yield
    finally:
        with closing(psycopg2.connect(TEST_DATABASE_URL)) as conn, conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP SCHEMA {schema} CASCADE")


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


class TestListProductObservations:
    def test_returns_current_parser_cards_with_their_flyer_context(self):
        first_flyer = _insert_flyer(slug="first-flyer", start_date="2026-08-10")
        second_flyer = _insert_flyer(slug="second-flyer", start_date="2026-08-17")
        first_card = _card("first")
        second_card = _card("second")
        second_card["status"] = "partial"
        second_card["warnings"] = ["missing_brand"]
        second_card["parser_version"] = "0.2.0"
        db.upsert_product_cards(first_flyer.id, [first_card])
        db.upsert_product_cards(second_flyer.id, [second_card])

        observations = db.list_product_observations(parser_version="0.1.0")

        assert len(observations) == 1
        assert observations[0]["flyer_id"] == first_flyer.id
        assert observations[0]["flyer_slug"] == "first-flyer"
        assert observations[0]["flyer_start_date"] == "2026-08-10"
        assert observations[0]["name"] == first_card["name"]
        assert observations[0]["status"] == "ok"


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


def test_apply_migrations_twice_preserves_existing_records():
    record = _insert_flyer(slug="migration-check")
    db.upsert_product_cards(record.id, [_card("migration-check")])

    db.apply_migrations()
    db.apply_migrations()

    refreshed = db.get_flyer_by_slug("migration-check")
    assert refreshed is not None
    assert refreshed[0].id == record.id
    assert refreshed[1] == 1
    with db._cursor() as cur:
        cur.execute(
            "SELECT payload, image_object_key, image_content_type, image_width, image_height "
            "FROM product_cards WHERE flyer_id = %s",
            (record.id,),
        )
        card = cur.fetchone()
    assert card["payload"]["card_hash"].startswith("hash-migration-check-")
    assert card["image_object_key"] is None


def test_fresh_initialization_has_current_schema():
    with db._cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND (
                  (table_name = 'flyers' AND column_name = 'slug')
                  OR (table_name = 'product_cards' AND column_name IN (
                      'image_object_key', 'image_content_type',
                      'image_width', 'image_height'
                  ))
              )
            """
        )
        columns = {(row["table_name"], row["column_name"]) for row in cur.fetchall()}

    assert ("flyers", "slug") in columns
    assert {
        ("product_cards", "image_object_key"),
        ("product_cards", "image_content_type"),
        ("product_cards", "image_width"),
        ("product_cards", "image_height"),
    } <= columns


def test_apply_migrations_upgrades_existing_schema_without_losing_data():
    with closing(db._connect()) as conn, conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE product_cards")
            cur.execute("DROP TABLE flyers")
            cur.execute(
                """
                CREATE TABLE flyers (
                    id SERIAL PRIMARY KEY,
                    source_url TEXT NOT NULL,
                    storage_key TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL DEFAULT '',
                    start_date TEXT,
                    end_date TEXT,
                    content_hash TEXT NOT NULL UNIQUE,
                    downloaded_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    status TEXT NOT NULL DEFAULT 'DISCOVERED',
                    CONSTRAINT flyers_source_url_unique UNIQUE (source_url)
                );
                CREATE TABLE product_cards (
                    id BIGSERIAL PRIMARY KEY,
                    flyer_id INTEGER NOT NULL REFERENCES flyers(id) ON DELETE CASCADE,
                    card_hash TEXT NOT NULL,
                    card_index INTEGER NOT NULL,
                    page INTEGER,
                    bbox JSONB,
                    raw_text TEXT,
                    brand TEXT,
                    name TEXT,
                    description TEXT,
                    quantity JSONB,
                    price DOUBLE PRECISION,
                    reference_price DOUBLE PRECISION,
                    unit_prices JSONB NOT NULL DEFAULT '[]'::jsonb,
                    discount_percent INTEGER,
                    lidl_plus BOOLEAN NOT NULL DEFAULT FALSE,
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    status TEXT NOT NULL,
                    parser_version TEXT NOT NULL,
                    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
                    notes JSONB NOT NULL DEFAULT '[]'::jsonb,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT product_cards_dedupe
                        UNIQUE (flyer_id, parser_version, card_hash)
                );
                """
            )
            cur.execute(
                """
                INSERT INTO flyers
                    (source_url, storage_key, category, name, content_hash, status)
                VALUES ('https://example.com/legacy.pdf', 'legacy.pdf',
                        'TEST', 'Legacy flyer', 'legacy-hash', 'STORED')
                RETURNING id
                """
            )
            flyer_id = cur.fetchone()[0]
            payload = {"card_hash": "legacy-card-hash", "preserved": True}
            cur.execute(
                """
                INSERT INTO product_cards
                    (flyer_id, card_hash, card_index, status, parser_version, payload)
                VALUES (%s, 'legacy-card-hash', 7, 'partial', '0.1.0', %s)
                """,
                (flyer_id, psycopg2.extras.Json(payload)),
            )

    db.apply_migrations()

    with db._cursor() as cur:
        cur.execute(
            """
            SELECT f.source_url, f.content_hash, f.slug,
                   pc.card_index, pc.payload, pc.image_object_key,
                   pc.image_content_type, pc.image_width, pc.image_height
            FROM flyers f
            JOIN product_cards pc ON pc.flyer_id = f.id
            WHERE f.id = %s
            """,
            (flyer_id,),
        )
        row = cur.fetchone()
    assert row["source_url"] == "https://example.com/legacy.pdf"
    assert row["content_hash"] == "legacy-hash"
    assert row["slug"] is None
    assert row["card_index"] == 7
    assert row["payload"] == payload
    assert row["image_object_key"] is None
    assert row["image_content_type"] is None
    assert row["image_width"] is None
    assert row["image_height"] is None

    db.apply_migrations()
    with db._cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS count FROM product_cards WHERE flyer_id = %s",
            (flyer_id,),
        )
        assert cur.fetchone()["count"] == 1
