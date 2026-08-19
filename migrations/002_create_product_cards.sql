-- Migration 002: create product_cards table
-- Apply with: psql $DATABASE_URL -f migrations/002_create_product_cards.sql
-- This migration is idempotent (uses IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS product_cards (
    id                BIGSERIAL PRIMARY KEY,
    flyer_id          INTEGER     NOT NULL REFERENCES flyers(id) ON DELETE CASCADE,
    card_hash         TEXT        NOT NULL,
    card_index        INTEGER     NOT NULL,
    page              INTEGER,
    bbox              JSONB,
    raw_text          TEXT,
    brand             TEXT,
    name              TEXT,
    description       TEXT,
    quantity          JSONB,
    price             DOUBLE PRECISION,
    reference_price   DOUBLE PRECISION,
    unit_prices       JSONB       NOT NULL DEFAULT '[]'::jsonb,
    discount_percent  INTEGER,
    lidl_plus         BOOLEAN     NOT NULL DEFAULT FALSE,
    currency          TEXT        NOT NULL DEFAULT 'EUR',
    status            TEXT        NOT NULL,
    parser_version    TEXT        NOT NULL,
    warnings          JSONB       NOT NULL DEFAULT '[]'::jsonb,
    notes             JSONB       NOT NULL DEFAULT '[]'::jsonb,
    payload           JSONB       NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT product_cards_dedupe UNIQUE (flyer_id, parser_version, card_hash)
);

CREATE INDEX IF NOT EXISTS product_cards_flyer_idx ON product_cards (flyer_id);
CREATE INDEX IF NOT EXISTS product_cards_name_idx ON product_cards (name);
CREATE INDEX IF NOT EXISTS product_cards_parser_idx ON product_cards (parser_version);
