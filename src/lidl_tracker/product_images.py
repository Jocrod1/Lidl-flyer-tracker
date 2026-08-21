from __future__ import annotations

import dataclasses
import logging
from pathlib import Path
from typing import Any

import pymupdf

from .cards import ProductCard
from .pdf_extract import open_document

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class ProductImageResult:
    card_index: int
    method: str
    content_type: str | None
    width: int | None
    height: int | None
    reason: str | None
    selected_image: dict[str, Any] | None
    candidates: list[dict[str, Any]]


def object_key_for_card(flyer_id: int, card_id: int, ext: str) -> str:
    return f"flyers/{flyer_id}/cards/{card_id}/product-image.{ext.lstrip('.')}"


def _rect_tuple(rect: Any) -> tuple[float, float, float, float]:
    return (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))


def _overlap(a, b) -> float:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def _candidate_score(card_bbox, image_bbox) -> float:
    overlap = _overlap(card_bbox, image_bbox)
    if overlap <= 0:
        return -1.0
    image_area = (image_bbox[2] - image_bbox[0]) * (image_bbox[3] - image_bbox[1])
    card_area = (card_bbox[2] - card_bbox[0]) * (card_bbox[3] - card_bbox[1])
    overlap_ratio = overlap / min(card_area, image_area)
    size_ratio = min(image_area / max(card_area, 1.0), card_area / max(image_area, 1.0))
    return overlap_ratio * 3 + size_ratio


def extract_card_image(
    pdf_path: str | Path,
    card: ProductCard,
    *,
    card_index: int,
    fallback_dpi: int = 220,
) -> tuple[bytes | None, ProductImageResult]:
    doc = open_document(pdf_path)
    try:
        page = doc[card.page - 1]
        card_bbox = tuple(card.bbox)
        candidates: list[dict[str, Any]] = []
        best = None
        best_score = -1.0
        for image in page.get_images(full=True):
            xref = image[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception as exc:
                logger.debug("image rect lookup failed xref=%s card=%s: %s", xref, card_index, exc)
                continue
            for rect in rects:
                bbox = _rect_tuple(rect)
                score = _candidate_score(card_bbox, bbox)
                candidate = {"xref": xref, "bbox": list(bbox), "score": score}
                candidates.append(candidate)
                if score > best_score:
                    best_score = score
                    best = candidate

        if best and best_score > 0:
            try:
                info = doc.extract_image(best["xref"])
                content_type = f"image/{info.get('ext')}" if info.get("ext") else None
                return (
                    info["image"],
                    ProductImageResult(
                        card_index=card_index,
                        method="embedded",
                        content_type=content_type,
                        width=info.get("width"),
                        height=info.get("height"),
                        reason=None,
                        selected_image=best,
                        candidates=candidates,
                    ),
                )
            except Exception as exc:
                reason = f"embedded_extraction_failed: {exc}"
        else:
            reason = "no_suitable_embedded_image"

        clip = pymupdf.Rect(card.bbox)
        pix = page.get_pixmap(clip=clip, dpi=fallback_dpi, alpha=True)
        return (
            pix.tobytes("png"),
            ProductImageResult(
                card_index=card_index,
                method="rendered_crop",
                content_type="image/png",
                width=pix.width,
                height=pix.height,
                reason=reason,
                selected_image=best,
                candidates=candidates,
            ),
        )
    finally:
        doc.close()
