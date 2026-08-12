# PDF structure findings — Lidl Spain flyers

Based on all four real flyers downloaded on 2026-08-12.

## The text layer is fully usable — OCR is not needed

| flyer | pages | spans | chars | pages without text |
|---|---|---|---|---|
| ALIMENTACIÓN 17/8 | 51 | 2,244 | 24,108 | none |

Every page has extractable text. **No OCR, no object detection, no VLM.**

## Lidl ships semantic fonts — this is the key finding

Font names carry meaning, which removes almost all guesswork:

| font | meaning |
|---|---|
| `LidlFontPrice-Pt` | the headline price, **Lidl Plus** variant |
| `LidlFontPrice-WoPt` | the headline price, regular (without Lidl Plus) |
| `LidlFontCondPro-Bold` | brand + product name |
| `LidlFontCondPro-Book` | description, quantity, unit price |
| `LidlFontCondPro-Regular` | small price qualifier tokens (`ud`) |
| `LidlFontPro-Book` | struck-through reference price |
| `LidlFontPro-Bold` | discount badge (`-21%`), `Con Lidl Plus` |

Consequences:

- A price does not need to be found by regex over all text; it is exactly
  "any span whose font starts with `LidlFontPrice`".
- Lidl Plus pricing is detected from the font alone, not from nearby text.
- Brand/name vs description is a font distinction, not a heuristic.
- Prices in these fonts are already **dot-decimal** (`2.59`), while body
  text uses Spanish commas (`5,48 €/kg`). Both are handled.

## Geometry

- Page box is 468 × 794 pt for every page.
- Cards sit on a 3-column grid; left edges cluster at x ≈ 14.2 / 170.1 / 326.0.
- A card's descriptive lines share an `x0` within ~3 pt and stack with
  vertical gaps under ~14 pt.
- The headline price sits beside the text block within the same column,
  sometimes slightly above or below it.
- Text order in the PDF is **not** reading order, so spatial grouping is
  mandatory; sorting by `y` then `x` is not enough.

## Grouping algorithm used

1. Discard price-qualifier tokens (`ud`, `kg`) — they sit adjacent to the
   price and otherwise hijack it.
2. Cluster descriptive spans sharing a left edge and vertically contiguous.
3. Merge vertically stacked fragments of the same card (Lidl sometimes
   emits the brand line as its own block).
4. Keep only clusters containing a bold line — a real card always has one.
5. Greedily match each price anchor to its nearest remaining cluster,
   weighting horizontal distance more (the grid keeps price and text in the
   same column).

## Layout quirks found in real data

- Fresh produce/meat/fish use approximate weights: `Aprox. 950 g`.
- Loose produce uses `A granel` or `Unidad` instead of a weight.
- Bakery uses per-100 g bases: `0,41 €/100 g`, and tiered pricing
  `1 a 3 uds 0,31 €/100 g / 4 uds 0,27 €/100 g`.
- `2,- €/kg` is Lidl shorthand for `2,00 €/kg`.
- Thousands separators appear: `1.700 ml (850 g peso escurrido)`.
- Multi-size products print every size: `350 / 360 / 400 g` — deliberately
  **not** collapsed into one number; all values are kept.
- When a Lidl Plus price exists, two unit prices are printed
  (`5,48 €/kg / 4,32 €/kg`): regular first, Lidl Plus second.
- Bazar (non-food) products legitimately have **no** weight and **no** unit
  price. This is recorded as a note, never as a parse failure.
