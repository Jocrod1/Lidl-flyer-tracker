"""Group PDF spans into product cards and extract structured fields.

Strategy (derived from the real 2026-08-17 Alimentacion flyer, not guessed):

1. Price spans are trivially identifiable: Lidl ships dedicated fonts,
   `LidlFontPrice-Pt` (Lidl Plus price) and `LidlFontPrice-WoPt` (regular
   price). Each such span anchors exactly one product card.
2. Descriptive text is left-aligned: brand/name in `LidlFontCondPro-Bold`
   and description/quantity/unit-price in `LidlFontCondPro-Book`. Spans of
   a single card share an `x0` within a couple of points and are stacked
   with small vertical gaps, so they cluster reliably.
3. Each text cluster is matched to its nearest price anchor.

No object detection or OCR is involved.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Iterable, Sequence

from .parsers import (
    PARSER_VERSION,
    Quantity,
    UnitPrice,
    is_lidl_plus,
    normalize_name,
    parse_discount,
    parse_price,
    parse_quantity,
    parse_unit_prices,
)
from .pdf_extract import PageInfo, Span

PRICE_FONT_PREFIX = "LidlFontPrice"
PRICE_FONT_LIDL_PLUS = "LidlFontPrice-Pt"

BOLD_TEXT_FONTS = ("LidlFontCondPro-Bold",)
BODY_TEXT_FONTS = ("LidlFontCondPro-Book", "LidlFontCondPro-Regular")

X_TOLERANCE = 3.0        # spans of one card share a left edge
Y_GAP_TOLERANCE = 14.0   # max vertical gap inside one text cluster
MIN_PRICE = 0.05
MAX_PRICE = 9999.0

# Small standalone tokens printed right next to the price ("2.59 ud") that
# denote what the price refers to. They are not descriptive card text and
# must never be mistaken for a product name.
PRICE_UNIT_TOKENS = {
    "ud",
    "ud.",
    "uds",
    "kg",
    "l",
    "m",
    "m2",
    "pack",
    "par",
    "docena",
}


@dataclasses.dataclass
class TextCluster:
    """A left-aligned, vertically contiguous run of descriptive spans."""

    spans: list[Span]

    @property
    def x0(self) -> float:
        return min(s.x0 for s in self.spans)

    @property
    def y0(self) -> float:
        return min(s.y0 for s in self.spans)

    @property
    def x1(self) -> float:
        return max(s.x1 for s in self.spans)

    @property
    def y1(self) -> float:
        return max(s.y1 for s in self.spans)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    @property
    def lines(self) -> list[Span]:
        return sorted(self.spans, key=lambda s: (s.y0, s.x0))

    @property
    def raw_text(self) -> str:
        return "\n".join(s.text for s in self.lines)


@dataclasses.dataclass
class ProductCard:
    """A candidate product card plus everything extracted from it."""

    page: int
    bbox: tuple[float, float, float, float]
    raw_text: str
    brand: str | None
    name: str | None
    description: str | None
    quantity: Quantity | None
    price: float | None
    reference_price: float | None
    unit_prices: list[UnitPrice]
    discount_percent: int | None
    lidl_plus: bool
    currency: str
    parser_version: str
    price_bbox: tuple[float, float, float, float] | None
    warnings: list[str]
    notes: list[str]

    @property
    def status(self) -> str:
        """Quality of the extraction.

        Only `name` and `price` are universally required: many Bazar
        (non-food) products legitimately carry no weight or unit price, so
        their absence is recorded as a note rather than a defect.
        """
        if self.price is None or not self.name:
            return "failed"
        if self.warnings:
            return "partial"
        return "ok"

    def to_dict(self) -> dict[str, Any]:
        quantity = None
        if self.quantity:
            quantity = {
                "value": self.quantity.value,
                "unit": self.quantity.unit,
                "count": self.quantity.count,
                "total": self.quantity.total,
                "approximate": self.quantity.approximate,
                "values": list(self.quantity.values),
                "raw": self.quantity.raw,
            }
        return {
            "page": self.page,
            "bbox": [round(v, 1) for v in self.bbox],
            "brand": self.brand,
            "name": self.name,
            "normalized_name": normalize_name(self.name) if self.name else None,
            "description": self.description,
            "quantity": quantity,
            "price": self.price,
            "reference_price": self.reference_price,
            "unit_prices": [
                {
                    "value": up.value,
                    "unit": up.unit,
                    "basis": up.basis,
                    "per_unit": up.per_unit,
                    "raw": up.raw,
                }
                for up in self.unit_prices
            ],
            "discount_percent": self.discount_percent,
            "lidl_plus": self.lidl_plus,
            "currency": self.currency,
            "status": self.status,
            "warnings": self.warnings,
            "notes": self.notes,
            "raw_text": self.raw_text,
            "parser_version": self.parser_version,
        }


# --- span classification -------------------------------------------------


def is_price_span(span: Span) -> bool:
    if not span.font.startswith(PRICE_FONT_PREFIX):
        return False
    value = parse_price(span.text)
    return value is not None and MIN_PRICE <= value <= MAX_PRICE


def is_price_unit_span(span: Span) -> bool:
    """A bare 'ud' / 'kg' token that qualifies a price."""
    return span.text.strip().lower() in PRICE_UNIT_TOKENS


def is_descriptive_span(span: Span) -> bool:
    if is_price_unit_span(span):
        return False
    return span.font.startswith(BOLD_TEXT_FONTS) or span.font.startswith(
        BODY_TEXT_FONTS
    )


def is_bold_span(span: Span) -> bool:
    return span.font.startswith(BOLD_TEXT_FONTS)


# --- clustering ----------------------------------------------------------


def cluster_text_spans(spans: Iterable[Span]) -> list[TextCluster]:
    """Cluster descriptive spans sharing a left edge and stacked vertically."""
    candidates = [s for s in spans if is_descriptive_span(s)]
    candidates.sort(key=lambda s: (round(s.x0, 1), s.y0))

    clusters: list[TextCluster] = []
    current: list[Span] = []

    for span in candidates:
        if not current:
            current = [span]
            continue

        previous = current[-1]
        same_column = abs(span.x0 - previous.x0) <= X_TOLERANCE
        vertical_gap = span.y0 - previous.y1
        contiguous = -4.0 <= vertical_gap <= Y_GAP_TOLERANCE

        if same_column and contiguous:
            current.append(span)
        else:
            clusters.append(TextCluster(current))
            current = [span]

    if current:
        clusters.append(TextCluster(current))

    return clusters


def _distance(cluster: TextCluster, price: Span) -> float:
    """Distance between a text cluster and a price span.

    Horizontal separation is weighted more heavily because Lidl's grid keeps
    a card's price inside the same column, while vertically the price may sit
    slightly above or below the text.
    """
    cx = (cluster.x0 + cluster.x1) / 2
    cy = (cluster.y0 + cluster.y1) / 2
    dx = abs(cx - price.cx)
    dy = abs(cy - price.cy)
    return (dx * 1.6) ** 2 + dy ** 2


def match_clusters_to_prices(
    clusters: Sequence[TextCluster], prices: Sequence[Span]
) -> list[tuple[TextCluster, Span | None]]:
    """Greedily pair each price anchor with its closest unused text cluster."""
    pairs: list[tuple[float, int, int]] = []
    for pi, price in enumerate(prices):
        for ci, cluster in enumerate(clusters):
            pairs.append((_distance(cluster, price), pi, ci))
    pairs.sort()

    used_prices: set[int] = set()
    used_clusters: set[int] = set()
    assignment: dict[int, int] = {}

    for _, pi, ci in pairs:
        if pi in used_prices or ci in used_clusters:
            continue
        used_prices.add(pi)
        used_clusters.add(ci)
        assignment[ci] = pi

    return [
        (cluster, prices[assignment[ci]] if ci in assignment else None)
        for ci, cluster in enumerate(clusters)
    ]


# --- field extraction ----------------------------------------------------


def _looks_like_brand(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def extract_fields(
    cluster: TextCluster, price_span: Span | None, page: PageInfo
) -> ProductCard:
    lines = cluster.lines
    warnings: list[str] = []
    notes: list[str] = []

    brand_parts: list[str] = []
    name_parts: list[str] = []
    description_parts: list[str] = []
    quantity: Quantity | None = None
    unit_prices: list[UnitPrice] = []

    bold_lines = [s for s in lines if s.font.startswith(BOLD_TEXT_FONTS)]
    body_lines = [s for s in lines if not s.font.startswith(BOLD_TEXT_FONTS)]

    # Leading fully-uppercase bold lines are the brand; the rest is the name.
    seen_name = False
    for span in bold_lines:
        if not seen_name and _looks_like_brand(span.text):
            brand_parts.append(span.text)
        else:
            seen_name = True
            name_parts.append(span.text)

    for span in body_lines:
        text = span.text
        found_unit_prices = parse_unit_prices(text)
        if found_unit_prices:
            unit_prices.extend(found_unit_prices)
            continue
        parsed_quantity = parse_quantity(text)
        if parsed_quantity and quantity is None:
            quantity = parsed_quantity
            continue
        description_parts.append(text)

    brand = " ".join(brand_parts) or None
    name = " ".join(name_parts) or None

    # A card whose bold text was entirely uppercase has a brand but no name.
    if name is None and brand:
        name = brand
        brand = None
        warnings.append("name_taken_from_uppercase_text")

    price = parse_price(price_span.text) if price_span else None
    if price is None:
        warnings.append("no_price_anchor")

    # Nearby small non-clustered text: discount and reference price.
    discount = None
    reference_price = None
    lidl_plus = price_span is not None and price_span.font == PRICE_FONT_LIDL_PLUS

    for span in page.spans:
        if span is price_span or not _near(span, cluster, price_span):
            continue
        if discount is None:
            discount = parse_discount(span.text)
        if is_lidl_plus(span.text):
            lidl_plus = True
        if (
            reference_price is None
            and span.font.startswith("LidlFontPro-Book")
            and not span.font.startswith(PRICE_FONT_PREFIX)
        ):
            candidate = parse_price(span.text)
            if candidate is not None and price is not None and candidate > price:
                reference_price = candidate

    if not quantity:
        notes.append("no_quantity")
    if not unit_prices:
        notes.append("no_unit_price")

    return ProductCard(
        page=page.number,
        bbox=cluster.bbox,
        raw_text=cluster.raw_text,
        brand=brand,
        name=name,
        description=" ".join(description_parts) or None,
        quantity=quantity,
        price=price,
        reference_price=reference_price,
        unit_prices=unit_prices,
        discount_percent=discount,
        lidl_plus=lidl_plus,
        currency="EUR",
        parser_version=PARSER_VERSION,
        price_bbox=price_span.bbox if price_span else None,
        warnings=warnings,
        notes=notes,
    )


def _near(span: Span, cluster: TextCluster, price_span: Span | None) -> bool:
    """Whether a span sits in the neighbourhood of a card."""
    x0 = min(cluster.x0, price_span.x0 if price_span else cluster.x0) - 40
    x1 = max(cluster.x1, price_span.x1 if price_span else cluster.x1) + 40
    y0 = min(cluster.y0, price_span.y0 if price_span else cluster.y0) - 45
    y1 = max(cluster.y1, price_span.y1 if price_span else cluster.y1) + 45
    return x0 <= span.cx <= x1 and y0 <= span.cy <= y1


# --- page / document entry points ---------------------------------------


MERGE_X_TOLERANCE = 10.0   # brand block vs body block left-edge drift
MERGE_Y_GAP = 26.0         # vertical gap allowed when stitching blocks


def merge_adjacent_clusters(clusters: list[TextCluster]) -> list[TextCluster]:
    """Stitch vertically stacked fragments of the same card.

    Lidl sometimes emits the brand line as its own block, slightly offset
    from the description block below it. Left unmerged, the brand fragment
    competes for a price anchor and produces a card with a brand but no
    product text.
    """
    ordered = sorted(clusters, key=lambda c: (c.y0, c.x0))
    merged: list[TextCluster] = []

    for cluster in ordered:
        target = None
        for candidate in merged:
            horizontally_aligned = (
                abs(candidate.x0 - cluster.x0) <= MERGE_X_TOLERANCE
                and _overlaps_horizontally(candidate, cluster)
            )
            gap = cluster.y0 - candidate.y1
            if horizontally_aligned and -6.0 <= gap <= MERGE_Y_GAP:
                target = candidate
        if target is not None:
            target.spans.extend(cluster.spans)
        else:
            merged.append(TextCluster(list(cluster.spans)))

    return merged


def _overlaps_horizontally(a: TextCluster, b: TextCluster) -> bool:
    return min(a.x1, b.x1) - max(a.x0, b.x0) > -2.0


def extract_page_cards(page: PageInfo) -> list[ProductCard]:
    prices = [s for s in page.spans if is_price_span(s)]

    clusters = merge_adjacent_clusters(cluster_text_spans(page.spans))

    # A product card always carries a bold brand/name line. Clusters without
    # one are page furniture (legal text, headers, price-unit tokens) and are
    # excluded so they cannot steal a price anchor from a real card.
    clusters = [c for c in clusters if any(is_bold_span(s) for s in c.spans)]

    cards: list[ProductCard] = []
    for cluster, price_span in match_clusters_to_prices(clusters, prices):
        if price_span is None:
            continue
        cards.append(extract_fields(cluster, price_span, page))
    return cards


def extract_document_cards(pages: Iterable[PageInfo]) -> list[ProductCard]:
    cards: list[ProductCard] = []
    for page in pages:
        cards.extend(extract_page_cards(page))
    return cards
