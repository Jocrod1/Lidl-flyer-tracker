"""Deterministic product search over extracted cards.

No embeddings/LLM: normalized substring + all-words matching, per the
project's "deterministic first" principle (see section 12 of the spec).
"""

from __future__ import annotations

from typing import Any

from .parsers import normalize_name


def matches(card: dict[str, Any], query: str) -> bool:
    """Whether a card (as produced by ProductCard.to_dict) matches a query.

    Matching is normalized-substring first (handles the common case of
    searching for the exact printed name), falling back to "all query words
    present, in any order" so minor rewording ("queso en salmuera" vs
    "queso fresco en salmuera") still matches.
    """
    haystack = " ".join(
        filter(
            None,
            [
                card.get("normalized_name"),
                normalize_name(card.get("brand") or ""),
                normalize_name(card.get("description") or ""),
            ],
        )
    )
    needle = normalize_name(query)
    if not needle:
        return False
    if needle in haystack:
        return True
    words = [w for w in needle.split(" ") if w]
    return bool(words) and all(w in haystack for w in words)


def search_cards(cards: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    return [c for c in cards if matches(c, query)]
