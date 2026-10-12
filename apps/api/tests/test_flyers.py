"""Router tests for /v1/flyers — persistence is mocked, no real database."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from lidl_tracker.models.flyer import FlyerRecord, FlyerStatus
from lidl_tracker.parsers import PARSER_VERSION
from lidl_tracker.storage import database

from api.main import app

client = TestClient(app)


def _record(**overrides) -> FlyerRecord:
    defaults = dict(
        id=1,
        slug="alimentacion-folleto-semanal-2026-08-17-a07bd0de",
        source_url="https://example.com/a.pdf",
        storage_key="flyers/2026/08/hash.pdf",
        category="ALIMENTACION",
        name="Folleto Semanal",
        content_hash="a07bd0deadbeef",
        status=FlyerStatus.STORED,
        start_date="2026-08-17",
        end_date="2026-08-23",
    )
    defaults.update(overrides)
    return FlyerRecord(**defaults)


class TestListFlyers:
    def test_returns_paginated_items(self):
        with patch(
            "api.routers.flyers.db.list_flyers",
            return_value=([(_record(), 12)], 1),
        ) as mock_list:
            response = client.get("/v1/flyers")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert body["items"][0]["slug"] == "alimentacion-folleto-semanal-2026-08-17-a07bd0de"
        assert body["items"][0]["product_count"] == 12
        assert body["items"][0]["status"] == "STORED"
        mock_list.assert_called_once_with(year=None, page=1, page_size=20)

    def test_forwards_year_and_pagination_params(self):
        with patch(
            "api.routers.flyers.db.list_flyers", return_value=([], 0)
        ) as mock_list:
            response = client.get(
                "/v1/flyers", params={"year": 2026, "page": 2, "page_size": 5}
            )

        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0, "page": 2, "page_size": 5}
        mock_list.assert_called_once_with(year=2026, page=2, page_size=5)

    def test_rejects_page_size_above_maximum(self):
        response = client.get("/v1/flyers", params={"page_size": 1000})

        assert response.status_code == 422

    def test_missing_slug_serializes_as_empty_string(self):
        """Legacy rows without a backfilled slug should not crash serialization."""
        with patch(
            "api.routers.flyers.db.list_flyers",
            return_value=([(_record(slug=None), 0)], 1),
        ):
            response = client.get("/v1/flyers")

        assert response.status_code == 200
        assert response.json()["items"][0]["slug"] == ""


class TestGetFlyer:
    def test_found_returns_summary(self):
        with patch(
            "api.routers.flyers.db.get_flyer_by_slug",
            return_value=(_record(), 3),
        ) as mock_get:
            response = client.get(
                "/v1/flyers/alimentacion-folleto-semanal-2026-08-17-a07bd0de"
            )

        assert response.status_code == 200
        body = response.json()
        assert body["product_count"] == 3
        assert body["category"] == "ALIMENTACION"
        mock_get.assert_called_once_with("alimentacion-folleto-semanal-2026-08-17-a07bd0de")

    def test_not_found_returns_404(self):
        with patch("api.routers.flyers.db.get_flyer_by_slug", return_value=None):
            response = client.get("/v1/flyers/unknown-slug")

        assert response.status_code == 404
        assert response.json() == {"detail": "Flyer not found"}


def _card(**overrides) -> dict:
    defaults = {
        "id": 314,
        "card_index": 0,
        "page": 1,
        "brand": "CHEF SELECT",
        "name": "Guacamole",
        "description": "96% aguacate.",
        "quantity": {
            "value": 500.0,
            "unit": "g",
            "count": None,
            "total": 500.0,
            "approximate": False,
            "values": [],
            "raw": "500 g",
        },
        "price": 3.75,
        "reference_price": None,
        "unit_prices": [
            {
                "value": 7.5,
                "unit": "kg",
                "basis": 1,
                "per_unit": 7.5,
                "raw": "7,50 €/kg",
            }
        ],
        "discount_percent": None,
        "lidl_plus": False,
        "currency": "EUR",
        "status": "ok",
        "parser_version": PARSER_VERSION,
        "warnings": [],
        "notes": ["no_unit_price"],
    }
    defaults.update(overrides)
    return defaults


class TestListFlyerProducts:
    slug = "alimentacion-folleto-semanal-2026-08-17-a07bd0de"

    def test_existing_flyer_returns_cards_for_active_parser_version(self):
        with (
            patch(
                "api.routers.flyers.db.get_flyer_by_slug",
                return_value=(_record(id=42), 1),
            ),
            patch(
                "api.routers.flyers.db.list_product_cards",
                return_value=([_card()], 1),
            ) as mock_list,
        ):
            response = client.get(f"/v1/flyers/{self.slug}/products")

        assert response.status_code == 200
        assert response.json() == {
            "items": [
                {
                    **_card(),
                    "id": "314",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }
        mock_list.assert_called_once_with(
            42,
            parser_version=PARSER_VERSION,
            page=1,
            page_size=20,
        )

    def test_unknown_flyer_returns_404_without_querying_cards(self):
        with (
            patch("api.routers.flyers.db.get_flyer_by_slug", return_value=None),
            patch("api.routers.flyers.db.list_product_cards") as mock_list,
        ):
            response = client.get("/v1/flyers/unknown-slug/products")

        assert response.status_code == 404
        assert response.json() == {"detail": "Flyer not found"}
        mock_list.assert_not_called()

    def test_flyer_with_no_cards_returns_empty_page(self):
        with (
            patch(
                "api.routers.flyers.db.get_flyer_by_slug",
                return_value=(_record(id=42), 0),
            ),
            patch(
                "api.routers.flyers.db.list_product_cards", return_value=([], 0)
            ),
        ):
            response = client.get(f"/v1/flyers/{self.slug}/products")

        assert response.status_code == 200
        assert response.json() == {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
        }

    def test_pagination_preserves_total_on_partial_and_empty_pages(self):
        with (
            patch(
                "api.routers.flyers.db.get_flyer_by_slug",
                return_value=(_record(id=42), 5),
            ),
            patch(
                "api.routers.flyers.db.list_product_cards",
                side_effect=[
                    (
                        [
                            _card(
                                id=315,
                                card_index=2,
                                status="partial",
                                warnings=["missing_brand"],
                            )
                        ],
                        5,
                    ),
                    ([], 5),
                ],
            ) as mock_list,
        ):
            page_response = client.get(
                f"/v1/flyers/{self.slug}/products",
                params={"page": 2, "page_size": 2},
            )
            past_end_response = client.get(
                f"/v1/flyers/{self.slug}/products",
                params={"page": 4, "page_size": 2},
            )

        assert page_response.status_code == 200
        page_body = page_response.json()
        assert page_body["total"] == 5
        assert page_body["page"] == 2
        assert page_body["page_size"] == 2
        assert len(page_body["items"]) == 1
        assert page_body["items"][0]["status"] == "partial"
        assert past_end_response.status_code == 200
        assert past_end_response.json() == {
            "items": [],
            "total": 5,
            "page": 4,
            "page_size": 2,
        }
        assert mock_list.call_args_list[0].kwargs == {
            "parser_version": PARSER_VERSION,
            "page": 2,
            "page_size": 2,
        }
        assert mock_list.call_args_list[1].kwargs == {
            "parser_version": PARSER_VERSION,
            "page": 4,
            "page_size": 2,
        }

    def test_invalid_pagination_is_rejected(self):
        assert (
            client.get(f"/v1/flyers/{self.slug}/products", params={"page": 0}).status_code
            == 422
        )
        assert (
            client.get(
                f"/v1/flyers/{self.slug}/products", params={"page_size": 101}
            ).status_code
            == 422
        )

    def test_nullable_fields_and_nested_quantity_are_response_validated(self):
        nullable_card = _card(
            brand=None,
            name=None,
            description=None,
            quantity=None,
            price=None,
            reference_price=None,
            unit_prices=[],
            discount_percent=None,
            page=None,
            status="failed",
        )
        with (
            patch(
                "api.routers.flyers.db.get_flyer_by_slug",
                return_value=(_record(id=42), 1),
            ),
            patch(
                "api.routers.flyers.db.list_product_cards",
                return_value=([nullable_card], 1),
            ),
        ):
            response = client.get(f"/v1/flyers/{self.slug}/products")

        assert response.status_code == 200
        body = response.json()["items"][0]
        assert body["page"] is None
        assert body["brand"] is None
        assert body["name"] is None
        assert body["quantity"] is None
        assert body["price"] is None
        assert body["unit_prices"] == []

    def test_cards_are_isolated_by_resolved_flyer_id(self):
        records = [
            (_record(id=42, slug="flyer-one"), 1),
            (_record(id=43, slug="flyer-two"), 1),
        ]
        with (
            patch(
                "api.routers.flyers.db.get_flyer_by_slug", side_effect=records
            ),
            patch(
                "api.routers.flyers.db.list_product_cards",
                side_effect=[
                    ([_card(id=101, name="First flyer product")], 1),
                    ([_card(id=202, name="Second flyer product")], 1),
                ],
            ) as mock_list,
        ):
            first = client.get("/v1/flyers/flyer-one/products")
            second = client.get("/v1/flyers/flyer-two/products")

        assert first.json()["items"][0]["name"] == "First flyer product"
        assert second.json()["items"][0]["name"] == "Second flyer product"
        assert [call.args[0] for call in mock_list.call_args_list] == [42, 43]


def test_product_card_database_query_filters_and_pages_by_flyer_and_version():
    cursor = Mock()
    cursor.fetchone.return_value = {"count": 3}
    cursor.fetchall.return_value = [{"id": 314, "card_index": 2}]

    @contextmanager
    def mock_cursor():
        yield cursor

    with patch("lidl_tracker.storage.database._cursor", mock_cursor):
        cards, total = database.list_product_cards(
            42, parser_version=PARSER_VERSION, page=2, page_size=2
        )

    assert cards == [{"id": 314, "card_index": 2}]
    assert total == 3
    count_call, page_call = cursor.execute.call_args_list
    assert "WHERE flyer_id = %(flyer_id)s" in count_call.args[0]
    assert "parser_version = %(parser_version)s" in count_call.args[0]
    assert count_call.args[1] == {
        "flyer_id": 42,
        "parser_version": PARSER_VERSION,
    }
    assert "WHERE flyer_id = %(flyer_id)s" in page_call.args[0]
    assert "parser_version = %(parser_version)s" in page_call.args[0]
    assert "ORDER BY card_index ASC, id ASC" in page_call.args[0]
    assert page_call.args[1] == {
        "flyer_id": 42,
        "parser_version": PARSER_VERSION,
        "limit": 2,
        "offset": 2,
    }
