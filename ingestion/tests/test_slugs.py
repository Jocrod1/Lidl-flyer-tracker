"""Unit tests for deterministic flyer slug generation."""

from __future__ import annotations

from lidl_tracker.slugs import flyer_slug, slugify


class TestSlugify:
    def test_lowercases_and_dashes(self):
        assert slugify("ALIMENTACIÓN") == "alimentacion"

    def test_strips_accents_and_punctuation(self):
        assert slugify("Folleto Nº 5 — Semana") == "folleto-no-5-semana"

    def test_empty_input_returns_empty_string(self):
        assert slugify("") == ""
        assert slugify(None) == ""

    def test_collapses_repeated_separators(self):
        assert slugify("a   b--c") == "a-b-c"


class TestFlyerSlug:
    def test_combines_category_name_date_and_hash_prefix(self):
        slug = flyer_slug("ALIMENTACIÓN", "Folleto Semanal", "2026-08-17", "a07bd0deadbeef")
        assert slug == "alimentacion-folleto-semanal-2026-08-17-a07bd0de"

    def test_missing_start_date_is_omitted(self):
        slug = flyer_slug("BAZAR", "Folleto", None, "abc12345")
        assert slug == "bazar-folleto-abc12345"

    def test_missing_category_and_name_falls_back_to_flyer(self):
        slug = flyer_slug("", "", "2026-08-17", "abc12345")
        assert slug == "flyer-2026-08-17-abc12345"

    def test_same_inputs_are_deterministic(self):
        args = ("ALIMENTACIÓN", "Folleto Semanal", "2026-08-17", "a07bd0deadbeef")
        assert flyer_slug(*args) == flyer_slug(*args)

    def test_different_content_hash_changes_slug_even_with_identical_metadata(self):
        """Two concurrent flyers with the same name/date/category never collide."""
        slug_a = flyer_slug("ALIMENTACIÓN", "Folleto Semanal", "2026-08-17", "aaaaaaaa")
        slug_b = flyer_slug("ALIMENTACIÓN", "Folleto Semanal", "2026-08-17", "bbbbbbbb")
        assert slug_a != slug_b
