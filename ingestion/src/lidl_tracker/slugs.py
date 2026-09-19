"""Deterministic slug generation.

Flyers are not given a stable identifier by the Schwarz leaflet API — the
only thing resembling a "slug" is derived from a URL and is never
persisted. Multiple flyers (e.g. ALIMENTACIÓN and BAZAR) can also be live
in the same week, so a slug scheme based only on the ISO week would not
be unique.

Instead we mint our own slug from data we already persist:

    {category + name, slugified} - {start_date, slugified} - {content_hash prefix}

The content-hash suffix guarantees uniqueness (content_hash is already a
UNIQUE column) even when two flyers share a category, name, and date.
"""

from __future__ import annotations

import re
import unicodedata

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

#: Number of hex characters from the content hash to use as a uniqueness
#: suffix. 8 hex chars = 32 bits — collisions are not cryptographically
#: impossible, but are astronomically unlikely at this dataset's scale
#: and are caught by the unique index on `flyers.slug` regardless.
HASH_SUFFIX_LENGTH = 8


def slugify(text: str | None) -> str:
    """Lowercase, ASCII-fold, and dash-separate *text*.

    Returns an empty string for falsy input rather than raising, so
    callers can compose slugs from optional fields without extra checks.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _NON_ALNUM_RE.sub("-", ascii_text.lower()).strip("-")
    return slug


def flyer_slug(
    category: str | None,
    name: str | None,
    start_date: str | None,
    content_hash: str,
) -> str:
    """Build a deterministic, URL-safe, unique flyer slug.

    `content_hash` is required and assumed non-empty — every persisted
    flyer already has one (it is the ingestion pipeline's dedupe key).
    """
    base = slugify(" ".join(part for part in (category, name) if part)) or "flyer"
    date_part = slugify(start_date)
    suffix = content_hash[:HASH_SUFFIX_LENGTH]
    return "-".join(part for part in (base, date_part, suffix) if part)
