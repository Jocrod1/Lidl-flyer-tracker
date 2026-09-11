from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont


def fit(image, width, height):
    image = image.copy()
    image.thumbnail((width, height))
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description="Create side-by-side ranking review images")
    parser.add_argument("rankings", type=Path)
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--inspection-dir", type=Path, required=True)
    parser.add_argument("--classification", choices=["clear", "probable", "ambiguous"],
                        required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    rows = [row for row in json.loads(args.rankings.read_text(encoding="utf-8"))
            if row["confidence"] == args.classification and row["selected_candidate"]]
    rows.sort(key=lambda row: (-row["score_gap_1_2"], -row["selected_candidate"]["score"]))
    (args.output / "individual").mkdir(parents=True, exist_ok=True)
    (args.output / "sheets").mkdir(parents=True, exist_ok=True)
    docs = {}
    csv_rows = []
    font = ImageFont.load_default()
    for number, row in enumerate(rows, 1):
        docs.setdefault(row["source_pdf"], pymupdf.open(args.pdf_dir / row["source_pdf"]))
        doc = docs[row["source_pdf"]]
        selected = row["selected_candidate"]
        candidates = row["top3"][:2] if args.classification == "ambiguous" else [selected]
        natives = [
            Image.open(io.BytesIO(doc.extract_image(candidate["xref"])["image"])).convert("RGB")
            for candidate in candidates
        ]
        crop = Image.open(args.inspection_dir / row["crop"]).convert("RGB")
        canvas = Image.new("RGB", (1500 if len(candidates) == 2 else 1200, 700), "white")
        draw = ImageDraw.Draw(canvas)
        draw.text((12, 10), f"{number:03d} {row['name'] or '(unnamed)'} | "
                  f"p{row['page']} c{row['card_index']} | xref {selected['xref']} | "
                  f"score {selected['score']:.4f} | gap {row['score_gap_1_2']:.4f}",
                  fill="black", font=font)
        panels = [(crop, 15, "inspection crop")]
        panels += [
            (native, 510 + index * 495,
             f"TOP-{index + 1} xref {candidate['xref']} score {candidate['score']:.4f}")
            for index, (native, candidate) in enumerate(zip(natives, candidates))
        ]
        for image, x, label in panels:
            image = fit(image, 470, 630)
            canvas.paste(image, (x + (470 - image.width) // 2, 55 + (630 - image.height) // 2))
            draw.rectangle((x, 50, x + 480, 695), outline="gray", width=2)
            draw.text((x + 8, 58), label, fill="black", font=font)
        path = args.output / "individual" / f"{number:03d}-p{row['page']:03d}-c{row['card_index']}.jpg"
        canvas.save(path, quality=90)
        features = selected["features"]
        csv_rows.append({
            "review_number": number, "source_pdf": row["source_pdf"], "page": row["page"],
            "card_index": row["card_index"], "product_name": row["name"],
            "selected_xref": selected["xref"], "ranking_score": selected["score"],
            "score_gap_to_2": row["score_gap_1_2"], "direction": features["direction"],
            "image_bbox": json.dumps(selected["bbox"]), "image_width_px": selected["width"],
            "image_height_px": selected["height"], "crop": row["crop"],
            "review_image": str(path.relative_to(args.output)),
        })
    for doc in docs.values():
        doc.close()
    if args.classification == "ambiguous":
        for item, row in zip(csv_rows, rows):
            second = row["top3"][1]
            item.update({
                "top2_xref": second["xref"], "top2_score": second["score"],
                "top2_bbox": json.dumps(second["bbox"]),
                "top2_distance": second["features"]["edge_distance_pt"],
                "top2_direction": second["features"]["direction"],
            })
    with (args.output / f"{args.classification}_cards.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = list(csv_rows[0]) if csv_rows else ["source_pdf", "page", "card_index"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)
    for start in range(0, len(csv_rows), args.batch_size):
        chunk = csv_rows[start:start + args.batch_size]
        sheet = Image.new("RGB", (600 * 4, 370 * 5), "white")
        for index, item in enumerate(chunk):
            image = Image.open(args.output / item["review_image"])
            image.thumbnail((592, 362))
            x, y = index % 4 * 600, index // 4 * 370
            sheet.paste(image, (x + (600 - image.width) // 2, y + (370 - image.height) // 2))
        sheet.save(args.output / "sheets" / f"{args.classification}-{start + 1:03d}-"
                   f"{start + len(chunk):03d}.jpg", quality=88)
    print(f"reviewed {len(csv_rows)} {args.classification} cards -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
