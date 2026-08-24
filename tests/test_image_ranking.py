from __future__ import annotations

from tools.image_ranking.ranker import direction, edge_distance, rank_cards, score_candidate


def test_edge_distance_and_direction():
    text = (10, 10, 20, 20)
    assert edge_distance(text, (25, 10, 35, 20)) == 5
    assert direction(text, (25, 10, 35, 20)) == "right"
    assert direction(text, (10, 25, 20, 35)) == "below"


def test_ranking_is_deterministic_and_tie_breaks_xref():
    base = {
        "_source_pdf": "x.pdf", "card_index": 1, "page": 1, "name": "x",
        "column": 3, "row": 1, "text_price_union": [100, 100, 120, 120],
        "crop": "crop.png", "page_size": [468, 794],
        "embedded_images_on_page": [
            {"xref": 20, "bbox": [70, 100, 90, 120], "width": 20, "height": 20},
            {"xref": 10, "bbox": [70, 100, 90, 120], "width": 20, "height": 20},
        ],
    }
    first = rank_cards([base])
    second = rank_cards([base])
    assert first == second
    assert first[0]["top3"][0]["xref"] == 10


def test_score_reports_all_components():
    card = {
        "card_index": 1, "column": 3, "row": 1,
        "text_price_union": [100, 100, 120, 120], "page_size": [468, 794],
    }
    image = {"xref": 1, "bbox": [70, 100, 90, 120], "width": 20, "height": 20}
    result = score_candidate(card, image, 400, [card])
    assert set(result["features"]["components"]) == {
        "edge_distance", "vertical_overlap", "horizontal_overlap", "direction",
        "row_proximity", "image_size", "neighbor_isolation", "decorative_penalty",
    }
