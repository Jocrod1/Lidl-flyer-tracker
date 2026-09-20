"""Pydantic response models for the v1 API.

Field names are plain snake_case (Python/REST convention) rather than
the frontend's camelCase — the Next.js data-access layer is responsible
for adapting these into `FlyerArchiveItem`/`Product` shapes. Keeping the
API's own contract independent of the frontend's current type names
means either side can evolve without the other needing to change in
lockstep.
"""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str = "ok"


class FlyerSummary(BaseModel):
    """One flyer, as persisted in `flyers` plus its card count.

    `slug` is always present for flyers ingested after migration 004;
    older rows must be backfilled via `backfill_flyer_slugs()` before
    they can be resolved by `GET /v1/flyers/{slug}`.
    """

    id: int
    slug: str
    name: str
    category: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str
    product_count: int


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


class FlyerListResponse(Page[FlyerSummary]):
    pass
