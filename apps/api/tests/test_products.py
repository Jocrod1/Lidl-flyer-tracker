"""Contract tests for the derived products listing."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from api.main import app
from lidl_tracker.parsers import PARSER_VERSION
from lidl_tracker.storage import database

client = TestClient(app)


def _observation(**overrides) -> dict:
    defaults = {
        "id": 101,
        "card_index": 0,
        "page": 1,
        "brand": "Milbona",
        "name": "Yogur natural",
        "description": None,
        "quantity": {
            "value": 500.0,
            "unit": "g",
            "count": None,
            "total": 500.0,
            "approximate": False,
            "values": [],
            "raw": "500 g",
        },
        "price": 1.99,
        "reference_price": None,
        "unit_prices": [],
        "discount_percent": None,
        "lidl_plus": False,
        "currency": "EUR",
        "status": "ok",
        "parser_version": PARSER_VERSION,
        "warnings": [],
        "notes": [],
        "flyer_id": 10,
        "flyer_slug": "flyer-2026-08-01",
        "flyer_start_date": "2026-08-01",
    }
    defaults.update(overrides)
    return defaults


def _quantity(value: float, unit: str, count: int | None, raw: str) -> dict:
    return {
        "value": value,
        "unit": unit,
        "count": count,
        "total": value * (count or 1),
        "approximate": False,
        "values": [],
        "raw": raw,
    }


def _list_products(observations: list[dict], **params):
    with patch(
        "api.routers.products.db.list_product_observations",
        return_value=observations,
    ) as mock_list:
        response = client.get("/v1/products", params=params)
    return response, mock_list


def test_groups_same_precise_product_across_flyers_and_preserves_observations():
    observations = [
        _observation(),
        _observation(
            id=202,
            card_index=2,
            brand="MILBONA",
            name="Yogur natural",
            quantity=_quantity(500, "g", None, "500 gramos"),
            price=None,
            status="partial",
            warnings=["missing_price"],
            flyer_id=11,
            flyer_slug="flyer-2026-08-08",
            flyer_start_date="2026-08-08",
        ),
    ]

    response, mock_list = _list_products(observations)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    product = body["items"][0]
    assert product["identity"] == "matched"
    assert product["observation_count"] == 2
    assert product["last_seen"] == "2026-08-08"
    assert product["price"] is None
    assert product["category"] is None
    assert product["image_url"] is None
    assert [item["flyer_slug"] for item in product["observations"]] == [
        "flyer-2026-08-08",
        "flyer-2026-08-01",
    ]
    assert product["observations"][0]["status"] == "partial"
    assert product["observations"][0]["warnings"] == ["missing_price"]
    assert product["observations"][0]["id"] == "202"
    mock_list.assert_called_once_with(parser_version=PARSER_VERSION)


def test_similar_names_and_different_pack_sizes_are_not_merged():
    observations = [
        _observation(
            id=1,
            name="Yogur natural",
            quantity=_quantity(500, "g", None, "500 g"),
        ),
        _observation(id=2, name="Yogur natural azucarado"),
        _observation(
            id=3,
            name="Yogur natural",
            quantity=_quantity(1, "kg", None, "1 kg"),
        ),
        _observation(
            id=4,
            name="Yogur natural",
            quantity=_quantity(500, "g", 2, "2 x 500 g"),
        ),
        _observation(
            id=5,
            name="Yogur natural",
            description="Con vainilla",
            quantity=_quantity(500, "g", None, "500 g"),
        ),
    ]

    response, _ = _list_products(observations)

    assert response.status_code == 200
    assert response.json()["total"] == 5
    assert all(item["identity"] == "matched" for item in response.json()["items"])


def test_missing_identity_fields_and_ambiguous_quantities_remain_observation_only():
    observations = [
        _observation(id=1, brand=None),
        _observation(id=2, brand=None, flyer_id=11),
        _observation(
            id=3,
            quantity={
                "value": None,
                "unit": "g",
                "count": None,
                "total": None,
                "approximate": False,
                "values": [350, 400],
                "raw": "350 / 400 g",
            },
        ),
        _observation(id=4, quantity=None),
        _observation(
            id=5,
            quantity={
                "value": 500,
                "unit": "g",
                "count": None,
                "total": 500,
                "approximate": True,
                "values": [],
                "raw": "aprox. 500 g",
            },
        ),
        _observation(
            id=6,
            brand=None,
            name=None,
            quantity=None,
            price=None,
            flyer_slug=None,
            flyer_start_date=None,
            status="failed",
        ),
    ]

    response, _ = _list_products(observations)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == len(observations)
    assert all(item["identity"] == "observation_only" for item in items)
    assert all(item["observation_count"] == 1 for item in items)
    assert len({item["derived_id"] for item in items}) == len(observations)
    assert all(item["category"] is None for item in items)
    assert all(item["image_url"] is None for item in items)
    failed = next(item for item in items if item["observations"][0]["id"] == "6")
    assert failed["brand"] is None
    assert failed["name"] is None
    assert failed["quantity"] is None
    assert failed["price"] is None
    assert failed["last_seen"] is None


def test_conservative_normalization_preserves_punctuation_and_matches_accents():
    observations = [
        _observation(id=1, brand="CRÈME+", name="Crème C+", flyer_id=10),
        _observation(
            id=2,
            brand="creme+",
            name="Creme C+",
            flyer_id=11,
            flyer_start_date="2026-08-08",
        ),
        _observation(
            id=3,
            brand="creme+",
            name="Creme C",
            flyer_id=12,
            flyer_start_date="2026-08-09",
        ),
    ]

    response, _ = _list_products(observations)

    assert response.status_code == 200
    products = response.json()["items"]
    assert len(products) == 2
    assert sorted(product["observation_count"] for product in products) == [1, 2]


def test_products_are_sorted_deterministically_and_paginated_after_grouping():
    observations = [
        _observation(id=1, name="Beta", flyer_start_date="2026-08-01"),
        _observation(id=2, name="Alpha", flyer_start_date="2026-08-01"),
        _observation(
            id=3,
            name="Gamma",
            flyer_id=12,
            flyer_start_date="2026-08-10",
        ),
        _observation(
            id=4,
            name="Alpha",
            flyer_id=13,
            flyer_start_date="not-a-date",
        ),
    ]
    # The two Alpha observations are grouped before page boundaries are applied.
    first, _ = _list_products(observations, page=1, page_size=2)
    second, _ = _list_products(observations, page=2, page_size=2)
    first_again, _ = _list_products(observations, page=1, page_size=2)

    assert first.status_code == second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["total"] == 3
    assert first_body["page"] == 1
    assert first_body["page_size"] == 2
    assert [item["name"] for item in first_body["items"]] == ["Gamma", "Alpha"]
    assert [item["name"] for item in second_body["items"]] == ["Beta"]
    assert first_again.json() == first_body
    alpha = first_body["items"][1]
    assert alpha["observation_count"] == 2
    assert alpha["last_seen"] == "2026-08-01"


def test_sort_ties_use_derived_id_as_a_stable_tiebreaker():
    observations = [
        _observation(
            id=1,
            name="Same name",
            quantity=_quantity(500, "g", None, "500 g"),
        ),
        _observation(
            id=2,
            name="Same name",
            quantity=_quantity(1, "kg", None, "1 kg"),
        ),
    ]
    page_one, _ = _list_products(observations, page=1, page_size=1)
    page_two, _ = _list_products(observations, page=2, page_size=1)

    assert page_one.status_code == page_two.status_code == 200
    derived_ids = [
        page_one.json()["items"][0]["derived_id"],
        page_two.json()["items"][0]["derived_id"],
    ]
    assert derived_ids == sorted(derived_ids)
    assert page_one.json()["total"] == 2


def test_empty_and_past_end_pages_return_empty_items_with_total():
    empty, _ = _list_products([])
    past_end, _ = _list_products([_observation()], page=2, page_size=1)

    assert empty.status_code == 200
    assert empty.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}
    assert past_end.status_code == 200
    assert past_end.json()["items"] == []
    assert past_end.json()["total"] == 1


def test_invalid_pagination_is_rejected():
    with patch("api.routers.products.db.list_product_observations") as mock_list:
        invalid_page = client.get("/v1/products", params={"page": 0})
        invalid_page_size = client.get("/v1/products", params={"page_size": 101})

    assert invalid_page.status_code == 422
    assert invalid_page_size.status_code == 422
    mock_list.assert_not_called()


def test_database_failure_returns_generic_error_without_internal_details():
    unavailable_client = TestClient(app, raise_server_exceptions=False)
    internal_detail = "database password sentinel-do-not-return"
    with patch(
        "api.routers.products.db.list_product_observations",
        side_effect=RuntimeError(internal_detail),
    ):
        response = unavailable_client.get("/v1/products")

    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert internal_detail not in response.text


def test_invalid_flyer_dates_do_not_become_last_seen():
    response, _ = _list_products(
        [
            _observation(
                flyer_start_date="2026-02-30",
                quantity=None,
            )
        ]
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["last_seen"] is None
    assert (
        response.json()["items"][0]["observations"][0]["flyer_start_date"]
        == "2026-02-30"
    )


def test_database_read_joins_flyer_context_and_filters_parser_version():
    cursor = Mock()
    cursor.fetchall.return_value = [{"id": 101, "flyer_slug": "flyer-1"}]

    @contextmanager
    def mock_cursor():
        yield cursor

    with patch("lidl_tracker.storage.database._cursor", mock_cursor):
        rows = database.list_product_observations(parser_version=PARSER_VERSION)

    assert rows == [{"id": 101, "flyer_slug": "flyer-1"}]
    query, params = cursor.execute.call_args.args
    assert "JOIN flyers AS f ON f.id = pc.flyer_id" in query
    assert "WHERE pc.parser_version = %(parser_version)s" in query
    assert "f.start_date AS flyer_start_date" in query
    assert "ORDER BY f.id ASC, pc.card_index ASC, pc.id ASC" in query
    assert "LIMIT" not in query
    assert params == {"parser_version": PARSER_VERSION}
