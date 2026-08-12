"""Unit tests for the deterministic parsers (no PDF required)."""

from __future__ import annotations

import pytest

from lidl_tracker.parsers import (
    normalize_name,
    normalize_unit,
    parse_discount,
    parse_price,
    parse_quantity,
    parse_unit_prices,
    to_float,
)


class TestToFloat:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("9,99", 9.99),
            ("9.99", 9.99),
            ("2,59", 2.59),
            ("0,85", 0.85),
            ("12", 12.0),
            ("9,99 €", 9.99),
            ("1.700", 1700.0),      # thousands separator
            ("1.234,50", 1234.50),
            ("2,-", 2.0),           # Lidl shorthand for 2,00
            ("", None),
            ("abc", None),
        ],
    )
    def test_parses(self, raw, expected):
        assert to_float(raw) == expected


class TestPrice:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("9,99 €", 9.99),
            ("9.99", 9.99),
            ("2,49", 2.49),
            ("2.59", 2.59),
            ("0.85", 0.85),
            ("99.99", 99.99),
        ],
    )
    def test_parses(self, raw, expected):
        assert parse_price(raw) == expected

    def test_rejects_non_price(self):
        assert parse_price("Queso fresco") is None


class TestUnitPrice:
    def test_simple(self):
        (up,) = parse_unit_prices("8,33 €/kg")
        assert (up.value, up.unit, up.basis) == (8.33, "kg", 1)

    def test_litre(self):
        (up,) = parse_unit_prices("4,98 €/l")
        assert (up.value, up.unit) == (4.98, "l")

    def test_two_prices_regular_and_lidl_plus(self):
        results = parse_unit_prices("5,48 €/kg / 4,32 €/kg")
        assert [r.value for r in results] == [5.48, 4.32]

    def test_per_100g_basis(self):
        (up,) = parse_unit_prices("0,41 €/100 g")
        assert (up.value, up.unit, up.basis) == (0.41, "g", 100)
        assert up.per_unit == 0.0041

    def test_shorthand_price(self):
        (up,) = parse_unit_prices("2,- €/kg")
        assert up.value == 2.0

    def test_none_when_absent(self):
        assert parse_unit_prices("Con leche de vaca") == []


class TestQuantity:
    def test_decimal_kg(self):
        q = parse_quantity("1,2 kg")
        assert (q.value, q.unit, q.total) == (1.2, "kg", 1.2)

    def test_grams(self):
        q = parse_quantity("500 g")
        assert (q.value, q.unit) == (500.0, "g")

    def test_litre(self):
        q = parse_quantity("1 l")
        assert (q.value, q.unit) == (1.0, "l")

    def test_multipack(self):
        q = parse_quantity("6 x 330 ml")
        assert (q.value, q.unit, q.count, q.total) == (330.0, "ml", 6, 1980.0)

    def test_multipack_decimal(self):
        q = parse_quantity("4 x 62,5 g")
        assert (q.value, q.count, q.total) == (62.5, 4, 250.0)

    def test_approximate(self):
        q = parse_quantity("Aprox. 950 g")
        assert (q.value, q.unit, q.approximate) == (950.0, "g", True)

    def test_thousands_with_parenthetical(self):
        q = parse_quantity("1.700 ml (850 g peso escurrido)")
        assert (q.value, q.unit) == (1700.0, "ml")
        assert "peso escurrido" in q.raw  # raw text preserved for debugging

    def test_multiple_advertised_sizes_are_not_collapsed(self):
        q = parse_quantity("350 / 360 / 400 g")
        assert q.value is None
        assert q.unit == "g"
        assert q.values == (350.0, 360.0, 400.0)

    def test_unit_only(self):
        q = parse_quantity("Unidad")
        assert (q.value, q.unit) == (1.0, "ud")

    def test_bulk(self):
        q = parse_quantity("A granel")
        assert (q.value, q.unit) == (None, "granel")

    def test_rejects_description(self):
        assert parse_quantity("Con cebolla caramelizada.") is None


class TestMisc:
    def test_discount(self):
        assert parse_discount("-21%") == 21
        assert parse_discount("Con Lidl Plus") is None

    def test_normalize_unit(self):
        assert normalize_unit("Kg") == "kg"
        assert normalize_unit("uds") == "ud"
        assert normalize_unit("gr") == "g"

    def test_normalize_name(self):
        assert (
            normalize_name("MILBONA Queso fresco en salmuera")
            == "milbona queso fresco en salmuera"
        )
        assert normalize_name("Queso  Fresco!") == "queso fresco"
        # accents and case folded so variants converge
        assert normalize_name("Taboulé") == normalize_name("TABOULE")
