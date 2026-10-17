"""Read-only derived product listing endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Query
from lidl_tracker.parsers import PARSER_VERSION
from lidl_tracker.storage import database as db

from ..product_catalog import derive_product_groups
from ..schemas import ProductsResponse

router = APIRouter(prefix="/v1/products", tags=["products"])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.get("", response_model=ProductsResponse)
def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> ProductsResponse:
    observations = db.list_product_observations(parser_version=PARSER_VERSION)
    products = derive_product_groups(observations)
    offset = (page - 1) * page_size
    return ProductsResponse(
        items=products[offset : offset + page_size],
        total=len(products),
        page=page,
        page_size=page_size,
    )
