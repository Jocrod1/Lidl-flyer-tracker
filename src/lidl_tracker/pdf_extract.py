"""PDF text/coordinate extraction for Lidl flyers (PyMuPDF).

This module is deliberately dumb: it only turns a PDF into spans with
coordinates and font information. All interpretation lives elsewhere so the
raw layer stays debuggable and reusable.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Iterator

import pymupdf


@dataclasses.dataclass(frozen=True)
class Span:
    """A single styled text run with its bounding box."""

    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font: str
    size: float
    color: int
    flags: int

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & 2 ** 4) or "bold" in self.font.lower()

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class PageInfo:
    number: int
    width: float
    height: float
    spans: list[Span]
    image_count: int
    drawing_count: int

    @property
    def text_char_count(self) -> int:
        return sum(len(s.text) for s in self.spans)


def open_document(pdf_path: str | Path) -> pymupdf.Document:
    return pymupdf.open(str(pdf_path))


def extract_page(page: pymupdf.Page, page_number: int) -> PageInfo:
    """Extract all non-empty spans from a page."""
    raw = page.get_text("dict")
    spans: list[Span] = []

    for block in raw.get("blocks", []):
        if block.get("type") != 0:  # 0 == text
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                x0, y0, x1, y1 = span["bbox"]
                spans.append(
                    Span(
                        page=page_number,
                        text=text,
                        x0=x0,
                        y0=y0,
                        x1=x1,
                        y1=y1,
                        font=span.get("font", ""),
                        size=round(span.get("size", 0.0), 2),
                        color=span.get("color", 0),
                        flags=span.get("flags", 0),
                    )
                )

    return PageInfo(
        number=page_number,
        width=page.rect.width,
        height=page.rect.height,
        spans=spans,
        image_count=len(page.get_images(full=True)),
        drawing_count=len(page.get_drawings()),
    )


def iter_pages(pdf_path: str | Path) -> Iterator[PageInfo]:
    doc = open_document(pdf_path)
    try:
        for index, page in enumerate(doc):
            yield extract_page(page, index + 1)
    finally:
        doc.close()


def extract_all(pdf_path: str | Path) -> list[PageInfo]:
    return list(iter_pages(pdf_path))
