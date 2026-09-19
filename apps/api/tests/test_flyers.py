"""Router tests for /v1/flyers — persistence is mocked, no real database."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient
from lidl_tracker.models.flyer import FlyerRecord, FlyerStatus

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
