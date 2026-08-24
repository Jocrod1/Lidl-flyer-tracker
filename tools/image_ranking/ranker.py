from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any


def area(r):
    return max(0, r[2] - r[0]) * max(0, r[3] - r[1])


def edge_distance(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def overlap_length(a0, a1, b0, b1):
    return max(0, min(a1, b1) - max(a0, b0))


def overlap(a, b):
    return overlap_length(a[0], a[2], b[0], b[2]) * overlap_length(
        a[1], a[3], b[1], b[3]
    )


def center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def direction(text_bbox, image_bbox):
    tx, ty = center(text_bbox)
    ix, iy = center(image_bbox)
    dx, dy = ix - tx, iy - ty
    if abs(dx) > abs(dy) * 1.25:
        return "right" if dx > 0 else "left"
    if abs(dy) > abs(dx) * 1.25:
        return "below" if dy > 0 else "above"
    if dx > 0:
        return "below-right" if dy > 0 else "above-right"
    return "below-left" if dy > 0 else "above-left"


EXPECTED_DIRECTIONS = {
    1: {"above": 1, "right": .9, "above-right": .95, "left": .35,
        "below": .25, "below-left": .25, "below-right": .35},
    2: {"above": .9, "left": .9, "right": .8, "above-left": .9,
        "above-right": .85, "below": .25, "below-left": .3, "below-right": .3},
    3: {"left": 1, "above": .9, "above-left": .95, "above-right": .8,
        "right": .65, "below": .25, "below-left": .3, "below-right": .3},
}

WEIGHTS = {
    "edge_distance": .25,
    "vertical_overlap": .16,
    "horizontal_overlap": .04,
    "direction": .13,
    "row_proximity": .08,
    "image_size": .04,
    "neighbor_isolation": .10,
    "decorative_penalty": .20,
}


def score_candidate(card: dict[str, Any], image: dict[str, Any], page_median: float,
                    page_cards: list[dict[str, Any]]) -> dict[str, Any]:
    text = tuple(card["text_price_union"])
    image_bbox = tuple(image["bbox"])
    text_width = max(text[2] - text[0], 1)
    text_height = max(text[3] - text[1], 1)
    distance = edge_distance(text, image_bbox)
    vertical = overlap_length(text[1], text[3], image_bbox[1], image_bbox[3])
    horizontal = overlap_length(text[0], text[2], image_bbox[0], image_bbox[2])
    direction_name = direction(text, image_bbox)
    image_width = image_bbox[2] - image_bbox[0]
    image_height = image_bbox[3] - image_bbox[1]
    page_width, page_height = card["page_size"]
    large = image_width / page_width > .75 or image_height / page_height > .75
    strip = image_height < 8 or image_width < 25
    neighbor_conflict = max(
        (
            overlap(image_bbox, tuple(other["text_price_union"])) / max(area(image_bbox), 1e-9)
            for other in page_cards
            if other["card_index"] != card["card_index"]
        ),
        default=0,
    )
    components = {
        "edge_distance": math.exp(-distance / 45),
        "vertical_overlap": min(1, vertical / min(text_height, max(image_height, 1))),
        "horizontal_overlap": min(1, horizontal / min(text_width, max(image_width, 1))),
        "direction": EXPECTED_DIRECTIONS[card["column"]].get(direction_name, .2),
        "row_proximity": math.exp(-abs(center(text)[1] - center(image_bbox)[1]) / 140),
        "image_size": math.exp(-abs(math.log(max(area(image_bbox), 1) / max(page_median, 1))) / 2),
        "neighbor_isolation": 1 - min(1, neighbor_conflict),
        "decorative_penalty": 0 if large or strip else 1,
    }
    score = sum(components[name] * weight for name, weight in WEIGHTS.items())
    return {
        "xref": image["xref"],
        "bbox": image["bbox"],
        "width": image["width"],
        "height": image["height"],
        "score": score,
        "features": {
            "edge_distance_pt": distance,
            "vertical_overlap_pt": vertical,
            "horizontal_overlap_pt": horizontal,
            "direction": direction_name,
            "page_column": card["column"],
            "page_row": card["row"],
            "displayed_width_pt": image_width,
            "displayed_height_pt": image_height,
            "neighbor_conflict": neighbor_conflict,
            "decorative_or_background": large or strip,
            "components": components,
            "weights": WEIGHTS,
        },
    }


def rank_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages = defaultdict(list)
    for card in cards:
        pages[(card["_source_pdf"], card["page"])].append(card)
    results = []
    for card in cards:
        page_cards = pages[(card["_source_pdf"], card["page"])]
        images = card["embedded_images_on_page"]
        median = statistics.median(
            area(tuple(image["bbox"])) for image in images
        ) if images else 1
        ranked = sorted(
            (score_candidate(card, image, median, page_cards) for image in images),
            key=lambda candidate: (-candidate["score"], candidate["xref"]),
        )
        top = ranked[:3]
        first = top[0]["score"] if top else 0
        second = top[1]["score"] if len(top) > 1 else 0
        score_gap = first - second
        suitable = [
            candidate for candidate in ranked
            if candidate["features"]["edge_distance_pt"] <= 90
            and candidate["features"]["components"]["decorative_penalty"] >= .5
        ]
        if not top or not suitable:
            confidence = "no_suitable_candidate"
        elif score_gap >= .18 and top[0]["features"]["edge_distance_pt"] <= 60:
            confidence = "clear"
        elif score_gap >= .08:
            confidence = "probable"
        else:
            confidence = "ambiguous"
        results.append({
            "source_pdf": card["_source_pdf"],
            "card_index": card["card_index"],
            "page": card["page"],
            "name": card.get("name"),
            "column": card["column"],
            "row": card["row"],
            "text_price_bbox": card["text_price_union"],
            "crop": card["crop"],
            "candidate_count": len(ranked),
            "top3": top,
            "selected_candidate": top[0] if top else None,
            "score_gap_1_2": score_gap,
            "confidence": confidence,
        })
    return results
