"""Conservative, read-only grouping of flyer-card observations."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from datetime import date
from typing import Any, Optional

from .schemas import DerivedProductResponse, ProductObservationResponse


def _identity_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = unicodedata.normalize("NFD", normalized)
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    normalized = " ".join(normalized.split())
    return normalized or None


def _quantity_identity(value: Any) -> Optional[tuple[str, str, Optional[int]]]:
    if not isinstance(value, dict):
        return None

    amount = value.get("value")
    unit = _identity_text(value.get("unit"))
    count = value.get("count")
    alternatives = value.get("values")
    if (
        isinstance(amount, bool)
        or not isinstance(amount, (int, float))
        or not math.isfinite(amount)
        or amount <= 0
        or unit is None
        or (
            count is not None
            and (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count <= 0
            )
        )
        or value.get("approximate") is not False
        or not isinstance(alternatives, list)
        or alternatives
    ):
        return None

    return (format(amount, ".15g"), unit, count)


def _valid_iso_date(value: Any) -> Optional[date]:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _stable_digest(identity_key: tuple[Any, ...]) -> str:
    encoded = json.dumps(
        identity_key,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _observation_order(observation: dict[str, Any]) -> tuple[int, int, int, int]:
    flyer_date = _valid_iso_date(observation.get("flyer_start_date"))
    return (
        flyer_date.toordinal() if flyer_date else 0,
        int(observation["flyer_id"]),
        int(observation["card_index"]),
        int(observation["id"]),
    )


def _identity_key(observation: dict[str, Any]) -> Optional[tuple[Any, ...]]:
    brand = _identity_text(observation.get("brand"))
    name = _identity_text(observation.get("name"))
    description = _identity_text(observation.get("description")) or ""
    quantity = _quantity_identity(observation.get("quantity"))
    if brand is None or name is None or quantity is None:
        return None

    currency = _identity_text(observation.get("currency"))
    return ("matched", brand, name, description, quantity, currency)


def _display_order(
    product: DerivedProductResponse,
) -> tuple[int, str, str, str]:
    last_seen = _valid_iso_date(product.last_seen)
    return (
        -(last_seen.toordinal() if last_seen else 0),
        _identity_text(product.name) or "",
        _identity_text(product.brand) or "",
        product.derived_id,
    )


def derive_product_groups(
    observations: list[dict[str, Any]],
) -> list[DerivedProductResponse]:
    """Group only observations with sufficiently precise matching evidence."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    identity_by_group: dict[tuple[Any, ...], str] = {}

    for observation in observations:
        identity_key = _identity_key(observation)
        if identity_key is None:
            # Observation-only identifiers distinguish source records but are
            # explicitly not canonical product identifiers.
            group_key = (
                "observation_only",
                int(observation["flyer_id"]),
                int(observation["id"]),
            )
            identity_by_group[group_key] = "observation_only"
        else:
            group_key = identity_key
            identity_by_group[group_key] = "matched"
        grouped.setdefault(group_key, []).append(observation)

    products: list[tuple[DerivedProductResponse, tuple[Any, ...]]] = []
    for group_key, group_observations in grouped.items():
        ordered = sorted(group_observations, key=_observation_order, reverse=True)
        latest = ordered[0]
        valid_dates = [
            parsed
            for item in ordered
            if (parsed := _valid_iso_date(item.get("flyer_start_date"))) is not None
        ]
        last_seen = max(valid_dates).isoformat() if valid_dates else None
        response_observations = [
            ProductObservationResponse.model_validate(
                {
                    **item,
                    "id": str(item["id"]),
                }
            )
            for item in ordered
        ]
        identity = identity_by_group[group_key]
        digest_key = (
            group_key
            if identity == "matched"
            else ("observation_only", group_key[1], group_key[2])
        )
        product = DerivedProductResponse(
            derived_id=_stable_digest(digest_key),
            identity=identity,
            brand=latest.get("brand"),
            name=latest.get("name"),
            description=latest.get("description"),
            quantity=latest.get("quantity"),
            price=latest.get("price"),
            currency=latest["currency"],
            last_seen=last_seen,
            category=None,
            image_url=None,
            observation_count=len(ordered),
            observations=response_observations,
        )
        products.append((product, group_key))

    products.sort(key=lambda item: _display_order(item[0]))
    return [product for product, _ in products]
