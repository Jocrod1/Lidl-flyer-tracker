-- Migration 004: add a stable, backend-owned slug to flyers
-- Apply with: psql $DATABASE_URL -f migrations/004_add_flyer_slug.sql
-- This migration is idempotent.
--
-- Flyers previously had no slug column at all -- the acquisition-time
-- slug derived from the Lidl URL only ever existed in memory/logs. This
-- adds a persisted, backend-minted slug (see lidl_tracker.slugs) used by
-- the API and the /flyers/[slug] frontend route.
--
-- The column is nullable so existing rows (ingested before this
-- migration) can be backfilled by `lidl_tracker.storage.database.
-- backfill_flyer_slugs()` -- e.g. via `cli_ingest --migrate`. New rows
-- always get a slug at insert time.

ALTER TABLE flyers
    ADD COLUMN IF NOT EXISTS slug TEXT;

-- Partial unique index (rather than a plain UNIQUE constraint) so rows
-- awaiting backfill (slug IS NULL) don't collide with each other.
CREATE UNIQUE INDEX IF NOT EXISTS flyers_slug_unique
    ON flyers (slug)
    WHERE slug IS NOT NULL;
