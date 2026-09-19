"""Read-only flyer endpoints.

Backed directly by `lidl_tracker.storage.database` — no separate service
layer yet; this module is deliberately thin. If flyer-related read logic
grows (e.g. Phase 3's per-flyer products), consider extracting a service
module rather than growing this file into a second data-access layer.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from lidl_tracker.storage import database as db

from ..schemas import FlyerListResponse, FlyerSummary

router = APIRouter(prefix="/v1/flyers", tags=["flyers"])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _to_summary(record, product_count: int) -> FlyerSummary:
    status = record.status.value if hasattr(record.status, "value") else record.status
    return FlyerSummary(
        id=record.id,
        slug=record.slug or "",
        name=record.name,
        category=record.category,
        start_date=record.start_date,
        end_date=record.end_date,
        status=status,
        product_count=product_count,
    )


@router.get("", response_model=FlyerListResponse)
def list_flyers(
    year: Optional[int] = Query(default=None, ge=1900, le=9999),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> FlyerListResponse:
    records, total = db.list_flyers(year=year, page=page, page_size=page_size)
    items = [_to_summary(record, count) for record, count in records]
    return FlyerListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{slug}", response_model=FlyerSummary)
def get_flyer(slug: str) -> FlyerSummary:
    result = db.get_flyer_by_slug(slug)
    if result is None:
        raise HTTPException(status_code=404, detail="Flyer not found")
    record, product_count = result
    return _to_summary(record, product_count)
