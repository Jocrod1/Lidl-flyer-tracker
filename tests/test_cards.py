"""Tests for spatial grouping and card field extraction.

Synthetic spans reproduce the exact geometry/fonts observed on page 13 of
the real 2026-08-17 Alimentacion flyer.
"""

from __future__ import annotations

import pytest

from lidl_tracker.cards import (
    cluster_text_spans,
    extract_page_cards,
    is_price_span,
    merge_adjacent_clusters,
)
from lidl_tracker.pdf_extract import PageInfo, Span

BOLD = "LidlFontCondPro-Bold"
BOOK = "LidlFontCondPro-Book"
PRICE = "LidlFontPrice-WoPt"
PRICE_PLUS = "LidlFontPrice-Pt"


def span(text, x0, y0, font, size=10.0, width=60.0, height=11.0):
    return Span(
        page=1,
        text=text,
        x0=x0,
        y0=y0,
        x1=x0 + width,
        y1=y0 + height,
        font=font,
        size=size,
        color=0,
        flags=0,
    )


def make_page(spans):
    return PageInfo(
        number=1, width=468, height=794, spans=spans, image_count=0, drawing_count=0
    )


GUACAMOLE = [
    span("CHEF SELECT", 14.2, 503.2, BOLD),
    span("Guacamole", 14.2, 514.7, BOLD),
    span("96% aguacate.", 14.2, 528.2, BOOK, size=8.0),
    span("500 g", 14.2, 538.2, BOOK, size=8.0),
    span("7,50 €/kg", 14.2, 548.2, BOOK, size=8.0),
    span("3.75", 81.1, 510.3, PRICE, size=50.0, width=60, height=56),
    span("ud", 68.2, 547.9, "LidlFontCondPro-Regular", size=8.0, width=9, height=8),
]


class TestPriceDetection:
    def test_price_font_is_recognised(self):
        assert is_price_span(span("3.75", 81, 510, PRICE, size=50))

    def test_lidl_plus_price_font_is_recognised(self):
        assert is_price_span(span("2.59", 40, 313, PRICE_PLUS, size=70))

    def test_body_text_is_not_a_price(self):
        assert not is_price_span(span("500 g", 14.2, 538, BOOK, size=8))

    def test_number_in_normal_font_is_not_a_price(self):
        # struck-through reference prices use a normal font
        assert not is_price_span(span("3.29", 133, 322, "LidlFontPro-Book", size=14))


class TestClustering:
    def test_left_aligned_lines_form_one_cluster(self):
        clusters = cluster_text_spans(GUACAMOLE)
        assert len(clusters) == 1
        assert clusters[0].raw_text.startswith("CHEF SELECT\nGuacamole")

    def test_price_unit_token_is_excluded(self):
        clusters = cluster_text_spans(GUACAMOLE)
        assert "ud" not in clusters[0].raw_text.split("\n")

    def test_distant_columns_do_not_merge(self):
        spans = [
            span("CHEF SELECT", 14.2, 503.2, BOLD),
            span("CHEF SELECT", 170.1, 501.7, BOLD),
        ]
        assert len(cluster_text_spans(spans)) == 2

    def test_split_brand_block_is_merged(self):
        spans = [
            span("OCEAN SEA", 14.2, 500.0, BOLD),
            # body block sits slightly lower with a larger gap
            span("Anillas de calamar", 14.2, 522.0, BOLD),
            span("500 g", 14.2, 534.0, BOOK, size=8.0),
        ]
        merged = merge_adjacent_clusters(cluster_text_spans(spans))
        assert len(merged) == 1


class TestFieldExtraction:
    @pytest.fixture()
    def card(self):
        cards = extract_page_cards(make_page(GUACAMOLE))
        assert len(cards) == 1
        return cards[0]

    def test_brand(self, card):
        assert card.brand == "CHEF SELECT"

    def test_name(self, card):
        assert card.name == "Guacamole"

    def test_description(self, card):
        assert card.description == "96% aguacate."

    def test_quantity(self, card):
        assert (card.quantity.value, card.quantity.unit) == (500.0, "g")

    def test_price(self, card):
        assert card.price == 3.75
        assert card.currency == "EUR"

    def test_unit_price(self, card):
        assert card.unit_prices[0].value == 7.50
        assert card.unit_prices[0].unit == "kg"

    def test_status_ok(self, card):
        assert card.status == "ok"

    def test_raw_text_is_preserved(self, card):
        assert "7,50 €/kg" in card.raw_text

    def test_bbox_recorded(self, card):
        assert card.bbox[0] == pytest.approx(14.2)

    def test_parser_version_recorded(self, card):
        assert card.parser_version


class TestLidlPlus:
    def test_lidl_plus_price_font_sets_flag(self):
        spans = [
            span("CHEF SELECT", 47.5, 206.7, BOLD),
            span("Tortilla de patatas", 47.5, 218.2, BOLD),
            span("600 g", 47.5, 253.2, BOOK, size=8.0),
            span("5,48 €/kg / 4,32 €/kg", 47.5, 263.2, BOOK, size=8.0),
            span("2.59", 40.3, 313.9, PRICE_PLUS, size=70.0, width=88, height=75),
        ]
        (card,) = extract_page_cards(make_page(spans))
        assert card.lidl_plus is True
        assert card.price == 2.59
        assert [u.value for u in card.unit_prices] == [5.48, 4.32]


class TestNonFoodCard:
    def test_product_without_weight_still_parses(self):
        spans = [
            span("SILVERCREST", 14.2, 100.0, BOLD),
            span("Grill de contacto", 14.2, 111.5, BOLD),
            span("Pantalla LED.", 14.2, 125.0, BOOK, size=8.0),
            span("99.99", 90.0, 105.0, PRICE, size=50.0, width=60, height=56),
        ]
        (card,) = extract_page_cards(make_page(spans))
        assert card.status == "ok"          # missing weight is not a defect
        assert card.price == 99.99
        assert "no_quantity" in card.notes
