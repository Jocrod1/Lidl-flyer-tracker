"""Tests for deterministic product search."""

from __future__ import annotations

from lidl_tracker.parsers import normalize_name
from lidl_tracker.search import matches, search_cards

MILBONA_CARD = {
    "brand": "MILBONA",
    "name": "Queso fresco en salmuera",
    "normalized_name": normalize_name("Queso fresco en salmuera"),
    "description": "Con leche de vaca.",
}

OTHER_CARD = {
    "brand": "MILBONA",
    "name": "Queso Gouda",
    "normalized_name": normalize_name("Queso Gouda"),
    "description": None,
}


class TestMatches:
    def test_exact_name(self):
        assert matches(MILBONA_CARD, "Queso fresco en salmuera")

    def test_partial_query_matches_via_all_words(self):
        assert matches(MILBONA_CARD, "queso en salmuera")

    def test_case_and_accent_insensitive(self):
        assert matches(MILBONA_CARD, "QUESO FRESCO EN SALMUERA")

    def test_unrelated_query_does_not_match(self):
        assert not matches(MILBONA_CARD, "air fryer")

    def test_different_product_same_brand_does_not_match(self):
        assert not matches(OTHER_CARD, "queso en salmuera")

    def test_empty_query_matches_nothing(self):
        assert not matches(MILBONA_CARD, "")


class TestSearchCards:
    def test_finds_matching_card_among_many(self):
        hits = search_cards([OTHER_CARD, MILBONA_CARD], "queso en salmuera")
        assert hits == [MILBONA_CARD]

    def test_no_matches_returns_empty_list(self):
        assert search_cards([OTHER_CARD], "air fryer") == []
