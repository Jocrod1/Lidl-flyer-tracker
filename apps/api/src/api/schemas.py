"""Pydantic response models for the v1 API.

Field names are plain snake_case (Python/REST convention) rather than
the frontend's camelCase — the Next.js data-access layer is responsible
for adapting these into `FlyerArchiveItem`/`Product` shapes. Keeping the
API's own contract independent of the frontend's current type names
means either side can evolve without the other needing to change in
lockstep.
"""

from __future__ import annotations

from typing import Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

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


class QuantityResponse(BaseModel):
    """Parsed quantity data as persisted on a product card."""

    value: Optional[float] = Field(description="Parsed size value, if available.")
    unit: Optional[str] = Field(description="Normalized size unit, if available.")
    count: Optional[int] = Field(description="Pack count, if available.")
    total: Optional[float] = Field(description="Calculated total size, if available.")
    approximate: bool = Field(description="Whether the printed quantity is approximate.")
    values: List[float] = Field(
        description="Multiple advertised values when no single size applies."
    )
    raw: str = Field(description="Original quantity text extracted from the flyer.")


class UnitPriceResponse(BaseModel):
    """One unit-price measurement extracted from a card."""

    value: float
    unit: str
    basis: int
    per_unit: float
    raw: str


class ProductCardResponse(BaseModel):
    """A flyer-specific card observation from the active parser version.

    Extraction statuses are `ok`, `partial` (usable required fields with
    warnings), or `failed` (missing a required name or price). All statuses
    are returned so incomplete observations remain available to consumers.
    """

    id: str = Field(description="Database ID serialized as a decimal string.")
    card_index: int = Field(description="Stable zero-based position within the flyer.")
    page: Optional[int] = Field(description="Source PDF page, when known.")
    brand: Optional[str] = Field(description="Extracted brand, if available.")
    name: Optional[str] = Field(description="Extracted product name, if available.")
    description: Optional[str] = Field(description="Extracted description, if available.")
    quantity: Optional[QuantityResponse] = Field(
        description="Structured quantity data, if extracted."
    )
    price: Optional[float] = Field(description="Extracted price, if available.")
    reference_price: Optional[float] = Field(
        description="Separately extracted reference price, if available."
    )
    unit_prices: List[UnitPriceResponse] = Field(
        description="Extracted unit-price measurements."
    )
    discount_percent: Optional[int] = Field(
        description="Extracted discount percentage, if available."
    )
    lidl_plus: bool = Field(description="Whether the card identifies a Lidl Plus price.")
    currency: str = Field(description="Currency recorded for the card.")
    status: Literal["ok", "partial", "failed"] = Field(
        description="Parser extraction quality; partial and failed cards are retained."
    )
    parser_version: str = Field(description="Parser version that produced this card.")
    warnings: List[str] = Field(description="Extraction warnings.")
    notes: List[str] = Field(description="Non-fatal extraction notes.")


class FlyerProductsResponse(Page[ProductCardResponse]):
    """One paginated page of a flyer's cards from the active parser version."""

    pass


class ProductObservationResponse(ProductCardResponse):
    """One original flyer-card observation retained in a derived product."""

    flyer_slug: Optional[str] = Field(
        description="Persisted source flyer slug, if available."
    )
    flyer_start_date: Optional[str] = Field(
        description="Stored flyer start-date string; may not be a valid ISO date."
    )


class DerivedProductResponse(BaseModel):
    """A provisional grouping of flyer-card observations, not a canonical product."""

    derived_id: str = Field(
        description="Opaque provisional identifier; not a canonical ID or route slug."
    )
    identity: Literal["matched", "observation_only"] = Field(
        description=(
            "Whether observations met the conservative cross-flyer identity rule "
            "or remain an ungrouped source observation."
        )
    )
    brand: Optional[str] = Field(description="Brand from the newest observation.")
    name: Optional[str] = Field(description="Name from the newest observation.")
    description: Optional[str] = Field(
        description="Description from the newest observation."
    )
    quantity: Optional[QuantityResponse] = Field(
        description="Structured quantity from the newest observation."
    )
    price: Optional[float] = Field(
        description="Price from the newest observation, if available."
    )
    currency: str = Field(description="Currency from the newest observation.")
    last_seen: Optional[str] = Field(
        description="Latest valid ISO flyer start date across these observations."
    )
    category: Optional[str] = Field(
        default=None, description="Unavailable until a reliable product source exists."
    )
    image_url: Optional[str] = Field(
        default=None, description="Unavailable until public image delivery exists."
    )
    observation_count: int = Field(ge=1)
    observations: List[ProductObservationResponse]


class ProductsResponse(Page[DerivedProductResponse]):
    """One page of provisional derived product groups."""

    pass
