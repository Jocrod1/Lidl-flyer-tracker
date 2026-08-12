"""Deterministic field parsers for Lidl flyer text.

Everything here is pure string -> value logic so it can be unit tested
without a PDF. No LLM, no OCR, no heuristics that need a model.
"""

from __future__ import annotations

import dataclasses
import re
import unicodedata

PARSER_VERSION = "0.1.0"

# Units seen in Lidl ES flyers, mapped to a canonical form.
UNIT_ALIASES: dict[str, str] = {
    "g": "g",
    "gr": "g",
    "gramos": "g",
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "mg": "mg",
    "ml": "ml",
    "cl": "cl",
    "l": "l",
    "lt": "l",
    "litro": "l",
    "litros": "l",
    "ud": "ud",
    "uds": "ud",
    "u": "ud",
    "unidad": "ud",
    "unidades": "ud",
    "pack": "pack",
    "m": "m",
    "cm": "cm",
    "m2": "m2",
    "lavados": "lavados",
    "capsulas": "ud",
    "raciones": "ud",
    "pieces": "ud",
    "piezas": "ud",
    "rollos": "ud",
    "granel": "granel",
}

_UNIT_PATTERN = "|".join(
    sorted((re.escape(u) for u in UNIT_ALIASES), key=len, reverse=True)
)

# Numbers as printed by Lidl:
#   "1.700" (thousands), "9,99", "350", and "2,-" (meaning 2,00)
_NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+,-|\d+(?:[.,]\d+)?"

_THOUSANDS_RE = re.compile(r"^\d{1,3}(?:\.\d{3})+$")
_PAREN_RE = re.compile(r"\(.*?\)")

PRICE_RE = re.compile(rf"^\s*({_NUM})\s*€?\s*$")
PRICE_IN_TEXT_RE = re.compile(rf"({_NUM})\s*€")

UNIT_PRICE_RE = re.compile(
    rf"({_NUM})\s*€\s*/\s*(?:(\d+)\s*)?({_UNIT_PATTERN})\b",
    re.IGNORECASE,
)

# "600 g", "1,2 kg", "1 l", "500 ml", optionally approximate ("Aprox. 950 g")
_APPROX = r"(?:aprox\.?|approx\.?|~)\s*"

QUANTITY_RE = re.compile(
    rf"^\s*({_APPROX})?({_NUM})\s*({_UNIT_PATTERN})\.?\s*$",
    re.IGNORECASE,
)

# "6 x 330 ml", "3 x 125 g"
MULTIPACK_RE = re.compile(
    rf"^\s*({_APPROX})?(\d+)\s*[x×]\s*({_NUM})\s*({_UNIT_PATTERN})\.?\s*$",
    re.IGNORECASE,
)

# Quantity expressed without a number: "Unidad", "A granel"
UNIT_ONLY_RE = re.compile(r"^\s*(unidad|ud\.?|a\s+granel|granel)\s*\.?\s*$", re.I)

# Several pack sizes sharing one unit: "350 / 360 / 400 g"
MULTI_VALUE_RE = re.compile(
    rf"^\s*({_NUM})(?:\s*/\s*({_NUM}))+\s*({_UNIT_PATTERN})\.?\s*$",
    re.IGNORECASE,
)
_MULTI_SPLIT_RE = re.compile(rf"({_NUM})")

DISCOUNT_RE = re.compile(r"-\s*(\d{1,3})\s*%")

LIDL_PLUS_RE = re.compile(r"lidl\s*plus", re.IGNORECASE)


def to_float(raw: str) -> float | None:
    """Parse a Spanish or English formatted decimal number.

    '9,99' -> 9.99, '9.99' -> 9.99, '1.234,50' -> 1234.50
    """
    if raw is None:
        return None
    text = raw.strip().replace("€", "").replace(" ", "").replace("\u00a0", "")
    if not text:
        return None

    # "2,-" is Lidl shorthand for "2,00"
    if text.endswith(",-"):
        text = text[:-2]

    if _THOUSANDS_RE.match(text):
        text = text.replace(".", "")
    elif "," in text and "." in text:
        # last separator is the decimal one
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return round(float(text), 4)
    except ValueError:
        return None


def normalize_unit(raw: str | None) -> str | None:
    if not raw:
        return None
    key = strip_accents(raw.strip().lower().rstrip("."))
    return UNIT_ALIASES.get(key, key or None)


def strip_accents(text: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def parse_price(text: str) -> float | None:
    """Parse a standalone price token such as '9,99 €' or '2.59'."""
    match = PRICE_RE.match(text.replace("\u00a0", " "))
    if match:
        return to_float(match.group(1))
    match = PRICE_IN_TEXT_RE.search(text)
    if match:
        return to_float(match.group(1))
    return None


@dataclasses.dataclass(frozen=True)
class UnitPrice:
    value: float
    unit: str
    raw: str
    basis: int = 1

    @property
    def per_unit(self) -> float:
        """Price for exactly one `unit` (e.g. '0,41 €/100 g' -> 0.0041 €/g)."""
        return round(self.value / self.basis, 6)


def parse_unit_prices(text: str) -> list[UnitPrice]:
    """Parse every '8,33 €/kg' or '0,41 €/100 g' occurrence in a line.

    Lidl often prints two ('5,48 €/kg / 4,32 €/kg') when a Lidl Plus price
    exists; both are returned in document order.
    """
    results: list[UnitPrice] = []
    for match in UNIT_PRICE_RE.finditer(text):
        value = to_float(match.group(1))
        basis = int(match.group(2)) if match.group(2) else 1
        unit = normalize_unit(match.group(3))
        if value is not None and unit:
            results.append(
                UnitPrice(value=value, unit=unit, raw=match.group(0), basis=basis)
            )
    return results


@dataclasses.dataclass(frozen=True)
class Quantity:
    value: float | None
    unit: str | None
    count: int | None
    raw: str
    approximate: bool = False
    values: tuple[float, ...] = ()

    @property
    def total(self) -> float | None:
        if self.value is None:
            return None
        return round(self.value * (self.count or 1), 4)


def parse_quantity(text: str) -> Quantity | None:
    """Parse '600 g', '1,2 kg', '6 x 330 ml', 'Aprox. 950 g' or 'Unidad'.

    Complex quantities are preserved via `count`, `values` and `raw` rather
    than being collapsed into a single misleading number.
    """
    original = text.strip()
    # "1.700 ml (850 g peso escurrido)" -> the parenthetical is a detail
    cleaned = _PAREN_RE.sub("", original).strip()

    match = MULTIPACK_RE.match(cleaned)
    if match:
        return Quantity(
            value=to_float(match.group(3)),
            unit=normalize_unit(match.group(4)),
            count=int(match.group(2)),
            raw=original,
            approximate=bool(match.group(1)),
        )

    match = QUANTITY_RE.match(cleaned)
    if match:
        return Quantity(
            value=to_float(match.group(2)),
            unit=normalize_unit(match.group(3)),
            count=None,
            raw=original,
            approximate=bool(match.group(1)),
        )

    match = MULTI_VALUE_RE.match(cleaned)
    if match:
        unit = normalize_unit(match.group(3))
        head = cleaned[: cleaned.lower().rfind(match.group(3).lower())]
        values = tuple(
            v for v in (to_float(m) for m in _MULTI_SPLIT_RE.findall(head)) if v
        )
        # Ambiguous by design: keep every advertised size, commit to none.
        return Quantity(
            value=None, unit=unit, count=None, raw=original, values=values
        )

    match = UNIT_ONLY_RE.match(cleaned)
    if match:
        token = strip_accents(match.group(1).lower())
        if "granel" in token:
            return Quantity(value=None, unit="granel", count=None, raw=original)
        return Quantity(value=1.0, unit="ud", count=None, raw=original)

    return None


def parse_discount(text: str) -> int | None:
    match = DISCOUNT_RE.search(text)
    return int(match.group(1)) if match else None


def is_lidl_plus(text: str) -> bool:
    return bool(LIDL_PLUS_RE.search(text))


def normalize_name(text: str) -> str:
    """Canonical-ish form used later for entity resolution."""
    lowered = strip_accents(text.lower())
    lowered = lowered.replace(",", ".")
    lowered = re.sub(r"[^a-z0-9%./ ]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()
