"""CLI: inspect the structure of a Lidl flyer PDF.

    python -m lidl_tracker.cli_inspect <pdf> --summary
    python -m lidl_tracker.cli_inspect <pdf> --page 5
    python -m lidl_tracker.cli_inspect <pdf> --page 5 --fonts
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

from .pdf_extract import extract_all, extract_page, open_document


def summary(pdf: Path) -> None:
    pages = extract_all(pdf)
    print(f"file        : {pdf.name}")
    print(f"size        : {pdf.stat().st_size:,} bytes")
    print(f"pages       : {len(pages)}")
    total_spans = sum(len(p.spans) for p in pages)
    total_chars = sum(p.text_char_count for p in pages)
    print(f"spans       : {total_spans:,}")
    print(f"characters  : {total_chars:,}")

    empty = [p.number for p in pages if not p.spans]
    print(f"pages w/o text layer: {empty or 'none'}")

    print("\nper-page overview")
    print(f"{'pg':>3} {'w x h':>13} {'spans':>6} {'chars':>7} {'imgs':>5} {'draws':>6}")
    for page in pages:
        print(
            f"{page.number:>3} {page.width:6.0f}x{page.height:<6.0f} "
            f"{len(page.spans):>6} {page.text_char_count:>7} "
            f"{page.image_count:>5} {page.drawing_count:>6}"
        )

    sizes = collections.Counter()
    fonts = collections.Counter()
    for page in pages:
        for span in page.spans:
            sizes[span.size] += 1
            fonts[span.font] += 1

    print("\ntop font sizes (size -> span count)")
    for size, count in sizes.most_common(20):
        print(f"  {size:>7} -> {count:>6}")

    print("\ntop fonts")
    for font, count in fonts.most_common(15):
        print(f"  {font:<40} {count:>6}")


def dump_page(pdf: Path, number: int, show_fonts: bool) -> None:
    doc = open_document(pdf)
    try:
        page = extract_page(doc[number - 1], number)
    finally:
        doc.close()

    print(f"--- PAGE {page.number}  ({page.width:.0f} x {page.height:.0f}) ---")
    print(f"spans={len(page.spans)} images={page.image_count} drawings={page.drawing_count}\n")

    for span in sorted(page.spans, key=lambda s: (round(s.y0), s.x0)):
        extra = ""
        if show_fonts:
            extra = f"  [{span.font} {span.size} {'B' if span.is_bold else ' '} #{span.color:06x}]"
        print(
            f"({span.x0:6.1f},{span.y0:6.1f})-({span.x1:6.1f},{span.y1:6.1f}) "
            f"{span.text!r}{extra}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a Lidl flyer PDF")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--page", type=int)
    parser.add_argument("--fonts", action="store_true")
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(f"not found: {args.pdf}", file=sys.stderr)
        return 1

    if args.page:
        dump_page(args.pdf, args.page, args.fonts)
    else:
        summary(args.pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
