-- Migration 001: create flyers table
-- Apply with: psql $DATABASE_URL -f migrations/001_create_flyers.sql
-- This migration is idempotent (uses IF NOT EXISTS).

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

    -- Same PDF bytes always produce the same hash → must be unique
    CONSTRAINT flyers_content_hash_unique UNIQUE (content_hash),

    -- Source URLs may change over time but we still prefer uniqueness
    -- to catch accidental re-ingestion of the same flyer URL.
    -- Drop this constraint if Lidl ever reuses PDF URLs for different flyers.
    CONSTRAINT flyers_source_url_unique   UNIQUE (source_url)
);

CREATE INDEX IF NOT EXISTS flyers_status_idx ON flyers (status);
