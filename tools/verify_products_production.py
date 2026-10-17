"""Read-only production schema and representative product-data audit."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingestion" / "src"))
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from api.product_catalog import derive_product_groups
from lidl_tracker.parsers import PARSER_VERSION


REQUIRED_COLUMNS = {
    "flyers": {"id", "slug", "start_date"},
    "product_cards": {
        "id",
        "flyer_id",
        "card_index",
        "page",
        "brand",
        "name",
        "description",
        "quantity",
        "price",
        "reference_price",
        "unit_prices",
        "discount_percent",
        "lidl_plus",
        "currency",
        "status",
        "parser_version",
        "warnings",
        "notes",
    },
}
SUMMARY_FIELDS = ("brand", "name", "description", "quantity", "price", "currency")


def _database_url(env_file: Path | None) -> str:
    if env_file is None:
        value = os.environ.get("DATABASE_URL")
    else:
        value = None
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, item = line.split("=", 1)
                if key.strip() == "DATABASE_URL":
                    value = item.strip().strip("\"'")
                    break
    if not value:
        raise ValueError("DATABASE_URL is not configured.")
    return value


def _identity_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = unicodedata.normalize("NFD", normalized)
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return " ".join(normalized.split()) or None


def _strict_iso_date(value: str) -> bool:
    try:
        return dt.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _read_database(
    database_url: str,
) -> tuple[
    dict[str, set[str]],
    int,
    int,
    int,
    int,
    int,
    list[dict],
    list[dict],
]:
    conn = psycopg2.connect(
        database_url,
        connect_timeout=8,
        options="-c default_transaction_read_only=on",
    )
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT current_setting('transaction_read_only') AS read_only, "
                "current_setting('server_version_num') AS server_version"
            )
            settings = cursor.fetchone()
            if settings["read_only"] != "on":
                raise RuntimeError("Database connection is not read-only.")

            cursor.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name IN ('flyers', 'product_cards')
                """
            )
            columns: dict[str, set[str]] = defaultdict(set)
            for row in cursor.fetchall():
                columns[row["table_name"]].add(row["column_name"])

            cursor.execute("SELECT COUNT(*) AS count FROM flyers")
            flyer_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) AS count FROM product_cards")
            card_count = cursor.fetchone()["count"]
            cursor.execute(
                "SELECT COUNT(*) AS count FROM product_cards "
                "WHERE parser_version = %s",
                (PARSER_VERSION,),
            )
            active_card_count = cursor.fetchone()["count"]
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM product_cards AS pc
                JOIN flyers AS f ON f.id = pc.flyer_id
                WHERE pc.parser_version = %s
                  AND (f.slug IS NULL OR f.start_date IS NULL)
                """,
                (PARSER_VERSION,),
            )
            missing_flyer_context = cursor.fetchone()["count"]

            cursor.execute(
                """
                SELECT f.id, f.category, f.name, f.start_date, f.slug,
                       COUNT(pc.id) AS active_cards
                FROM flyers AS f
                LEFT JOIN product_cards AS pc
                  ON pc.flyer_id = f.id AND pc.parser_version = %s
                GROUP BY f.id
                ORDER BY f.start_date DESC NULLS LAST, f.id DESC
                """,
                (PARSER_VERSION,),
            )
            flyers = cursor.fetchall()
            cursor.execute(
                """
                WITH ranked AS (
                    SELECT
                        pc.id, pc.card_index, pc.page, pc.brand, pc.name,
                        pc.description, pc.quantity, pc.price,
                        pc.reference_price, pc.unit_prices,
                        pc.discount_percent, pc.lidl_plus, pc.currency,
                        pc.status, pc.parser_version, pc.warnings, pc.notes,
                        f.id AS flyer_id, f.slug AS flyer_slug,
                        f.start_date AS flyer_start_date,
                        f.category AS flyer_category,
                        f.name AS flyer_name,
                        ROW_NUMBER() OVER (
                            PARTITION BY f.id
                            ORDER BY pc.card_index, pc.id
                        ) AS row_number
                    FROM product_cards AS pc
                    JOIN flyers AS f ON f.id = pc.flyer_id
                    WHERE pc.parser_version = %s
                )
                SELECT *
                FROM ranked
                WHERE row_number <= 35
                ORDER BY flyer_start_date DESC NULLS LAST, flyer_id DESC,
                         card_index
                """,
                (PARSER_VERSION,),
            )
            observations = [dict(row) for row in cursor.fetchall()]
            return (
                dict(columns),
                flyer_count,
                card_count,
                active_card_count,
                missing_flyer_context,
                int(settings["server_version"]),
                [dict(row) for row in flyers],
                observations,
            )
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Read DATABASE_URL from this local env file; never print its value.",
    )
    args = parser.parse_args()

    try:
        database_url = _database_url(args.env_file)
        (
            columns,
            flyer_count,
            card_count,
            active_card_count,
            missing_flyer_context,
            server_version,
            flyers,
            observations,
        ) = _read_database(database_url)
    except (OSError, ValueError, psycopg2.Error, RuntimeError) as exc:
        print(f"Production audit could not complete ({type(exc).__name__}).", file=sys.stderr)
        return 2

    missing = {
        table: sorted(required - columns.get(table, set()))
        for table, required in REQUIRED_COLUMNS.items()
        if required - columns.get(table, set())
    }
    print(f"database_read_only=true postgres_major={server_version // 10000}")
    print(f"required_columns_present={not missing} missing_columns={missing}")
    print(
        f"flyers={flyer_count} product_cards={card_count} "
        f"active_parser={PARSER_VERSION} active_parser_cards={active_card_count} "
        f"active_cards_missing_flyer_context={missing_flyer_context}"
    )

    title_types = Counter()
    for flyer in flyers:
        title = (flyer["name"] or "").casefold()
        if "alimentación" in title:
            title_types["alimentacion"] += 1
        elif "bazar" in title:
            title_types["bazar"] += 1
        elif "especial" in title:
            title_types["especial"] += 1
        else:
            title_types["other"] += 1
    print(
        f"sample_flyers={len(flyers)} "
        f"source_category_values={sorted({str(f['category']) for f in flyers})} "
        f"flyer_title_types={dict(sorted(title_types.items()))}"
    )

    products = derive_product_groups(observations)
    matched = [product for product in products if product.identity == "matched"]
    repeated = [product for product in matched if product.observation_count > 1]
    cross_flyer = [
        product
        for product in repeated
        if len({observation.flyer_slug for observation in product.observations}) > 1
    ]
    source_ids = [str(observation["id"]) for observation in observations]
    response_ids = [
        observation.id
        for product in products
        for observation in product.observations
    ]
    summary_matches = sum(
        all(
            getattr(product, field) == getattr(product.observations[0], field)
            for field in SUMMARY_FIELDS
        )
        for product in products
    )
    source_statuses = {observation["status"] for observation in observations}
    returned_statuses = {
        observation.status
        for product in products
        for observation in product.observations
    }
    missing_fields = {
        field: sum(observation[field] is None for observation in observations)
        for field in ("brand", "name", "price", "quantity")
    }
    last_seen_values = [
        product.last_seen for product in products if product.last_seen is not None
    ]
    last_seen_valid = sum(_strict_iso_date(value) for value in last_seen_values)
    source_rows_preserved = sorted(source_ids) == sorted(response_ids)
    unique_response_ids = len(set(response_ids))
    statuses_preserved = source_statuses == returned_statuses
    summaries_match = summary_matches == len(products)
    categories_null = all(product.category is None for product in products)
    images_null = all(product.image_url is None for product in products)
    quality_failures = []
    if not source_rows_preserved or unique_response_ids != len(source_ids):
        quality_failures.append("source observations were not preserved exactly")
    if not statuses_preserved:
        quality_failures.append("source statuses changed")
    if not summaries_match:
        quality_failures.append("a product summary differs from its newest observation")
    if last_seen_valid != len(last_seen_values):
        quality_failures.append("a last_seen value is not a strict ISO date")
    if not categories_null or not images_null:
        quality_failures.append("category or image URL is unexpectedly populated")
    if missing_flyer_context:
        quality_failures.append("active observations are missing flyer context")

    print(
        f"sample_observations={len(observations)} "
        f"sample_derived_groups={len(products)} "
        f"matched_groups={len(matched)} "
        f"observation_only_groups={len(products) - len(matched)} "
        f"groups_with_multiple_observations={len(repeated)} "
        f"groups_spanning_flyers={len(cross_flyer)}"
    )
    print(
        f"source_rows_preserved={source_rows_preserved} "
        f"unique_observation_ids={len(set(response_ids))}/{len(source_ids)} "
        f"summaries_matching_newest_observation={summary_matches}/{len(products)} "
        f"source_statuses={sorted(source_statuses)} "
        f"returned_statuses={sorted(returned_statuses)}"
    )
    print(
        f"sample_missing_fields={missing_fields} "
        f"valid_iso_last_seen={last_seen_valid}/{len(last_seen_values)} "
        f"all_category_null={categories_null} "
        f"all_image_url_null={images_null}"
    )

    by_brand_name: dict[tuple[str | None, str | None], list] = defaultdict(list)
    for product in matched:
        observation = product.observations[0]
        by_brand_name[
            (_identity_text(observation.brand), _identity_text(observation.name))
        ].append(product)
    variant_sets = [group for group in by_brand_name.values() if len(group) > 1]
    quantity_value_variants = sum(
        len({product.quantity.value for product in group}) > 1
        for group in variant_sets
    )
    quantity_unit_variants = sum(
        len({_identity_text(product.quantity.unit) for product in group}) > 1
        for group in variant_sets
    )
    pack_count_variants = sum(
        len({product.quantity.count for product in group}) > 1
        for group in variant_sets
    )
    description_variants = sum(
        len({_identity_text(product.description) for product in group}) > 1
        for group in variant_sets
    )
    currency_variants = sum(
        len({_identity_text(product.currency) for product in group}) > 1
        for group in variant_sets
    )
    print(
        f"same_brand_name_variant_sets={len(variant_sets)} "
        f"quantity_value_difference_sets={quantity_value_variants} "
        f"quantity_unit_difference_sets={quantity_unit_variants} "
        f"pack_count_difference_sets={pack_count_variants} "
        f"description_difference_sets={description_variants} "
        f"currency_difference_sets={currency_variants}"
    )
    if quality_failures:
        print(f"quality_failures={quality_failures}")
    return 0 if not missing and not quality_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
