# Native PDF image-ranking research tool

This is an offline research/evaluation component. It is intentionally not
called by production ingestion or database code.

For each card, the evaluator reads the inspection JSON, enumerates
`Page.get_images(full=True)` placements and resolves their coordinates with
`Page.get_image_rects(xref)`. It ranks placements using the recovered,
unchanged deterministic score: edge distance, vertical/horizontal overlap,
direction, column, row proximity, displayed size, isolation from neighboring
card text, and page-sized/tiny decorative penalties. The selected native
image is extracted with `Document.extract_image(xref)` and its encoded
`info["image"]` bytes are preserved. Review generation separately uses
`Page.get_pixmap()` output already present in the inspection dataset.

## Reproduce the evaluation

The inspection dataset is generated outside the repository and is not
committed because it contains 635 crops and large PDF-derived data. Given
that directory:

```bash
python -m tools.image_ranking.evaluate /path/to/pdf_card_inspection \
  --output /tmp/per_card_rankings.json
```

To reproduce review images (requires Pillow):

```bash
python -m tools.image_ranking.review /tmp/per_card_rankings.json \
  --pdf-dir data/raw --inspection-dir /path/to/pdf_card_inspection \
  --classification ambiguous --output /tmp/ambiguous-review
```

Use `clear`, `probable`, or `ambiguous` for the classification. The source
PDFs must have the same filenames recorded in the inspection JSON.

## Tests

This tool has its own test suite, separate from `ingestion/tests`, run
explicitly with:

```bash
python -m pytest tools/image_ranking/tests
```

The original four-flyer evaluation contained 635 cards: 83 clear, 183
probable, 353 ambiguous, and 16 with no suitable candidate. The method uses
only native PDF geometry/layout; it uses no OCR, object detection, LLM/VLM,
embeddings, or visual recognition. Candidate ranking is not semantic
ground truth: a visually correct image may still be classified ambiguous.

## Purpose

This tool exists to evaluate whether native PDF image XObjects can be
reliably associated with extracted product cards.

It is currently used to:

- evaluate image-to-card association heuristics
- manually review candidate images
- identify high-confidence native product images
- provide a baseline for future improvements to image grouping

The current production strategy does not depend on this evaluator.

## Known limitations

The PDF does not contain an explicit semantic relationship between a
product-card text block and its product image.

Therefore the ranking algorithm can identify likely candidates, but
cannot guarantee semantic correctness.

Some ambiguous cases may represent a single product visual composed of
multiple native image XObjects (for example, several coffee-box images
representing different varieties of the same offer). These cases are
intentionally left for future image-grouping work.

## Current baseline

Evaluation over four flyers / 635 cards:

- Clear: 83 (13.1%)
- Probable: 183 (28.8%)
- Ambiguous: 353 (55.6%)
- No suitable candidate: 16 (2.5%)

The clear and probable candidates have been manually reviewed and are
considered suitable candidates for the next stage of native image
persistence.
