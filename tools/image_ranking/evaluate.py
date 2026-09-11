from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.image_ranking.ranker import rank_cards


def load_inspection(path: Path) -> list[dict]:
    cards = []
    for source in sorted(path.glob("*.json")):
        if source.name in {"index.json", "aggregate_statistics.json"}:
            continue
        data = json.loads(source.read_text(encoding="utf-8"))
        for card in data["cards"]:
            card["_source_pdf"] = data["pdf"]
            cards.append(card)
    return cards


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank native PDF images for extracted cards")
    parser.add_argument("inspection_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = rank_cards(load_inspection(args.inspection_dir))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ranked {len(results)} cards -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
