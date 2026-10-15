import {
  fetchFlyerBySlug,
  fetchFlyerList,
  fetchFlyerProducts,
  FlyerApiError,
  type FlyerSummaryDTO,
} from "./api";
import { mapFlyerSummary } from "./mapper";
import type { FlyerArchiveItem } from "./types";
import type { FlyerProductCard } from "@/lib/products";

export { FlyerApiError, FlyerNotFoundError, MissingApiBaseUrlError } from "./api";

/** Maximum page size enforced by GET /v1/flyers. */
const ARCHIVE_PAGE_SIZE = 100;

async function fetchAllFlyers(year?: number): Promise<{
  items: FlyerSummaryDTO[];
  total: number;
}> {
  const firstPage = await fetchFlyerList({
    page: 1,
    page_size: ARCHIVE_PAGE_SIZE,
    year,
  });
  const items = [...firstPage.items];
  const pageCount = Math.ceil(firstPage.total / firstPage.page_size);

  for (let page = 2; page <= pageCount; page += 1) {
    const nextPage = await fetchFlyerList({
      page,
      page_size: firstPage.page_size,
      year,
    });
    items.push(...nextPage.items);
  }

  return { items, total: firstPage.total };
}

export interface FlyerArchivePage {
  currentFlyer: FlyerArchiveItem | null;
  pastFlyers: FlyerArchiveItem[];
  totalFlyerCount: number;
  years: number[];
  activeYear: number | "all";
}

function distinctYears(items: FlyerSummaryDTO[]): number[] {
  const years = new Set<number>();
  for (const item of items) {
    const year = item.start_date?.slice(0, 4);
    if (year && /^\d{4}$/.test(year)) {
      years.add(Number(year));
    }
  }
  return Array.from(years).sort((a, b) => b - a);
}

/**
 * Loads the complete archive for the Flyer Archive (`/flyers`) page.
 *
 * Always fetches the unfiltered archive first (to resolve the current
 * flyer, the year facets, and the total count), then — only when
 * `year` is a real, present year — loads the filtered API pages using
 * `?year=` rather than reproducing the filter client-side.
 */
export async function getFlyerArchive(
  options: { year?: number } = {},
): Promise<FlyerArchivePage> {
  const base = await fetchAllFlyers();

  const years = distinctYears(base.items);
  const currentDto = base.items[0];
  const currentFlyer = currentDto
    ? mapFlyerSummary(currentDto, { isCurrent: true })
    : null;

  const activeYear: number | "all" =
    options.year !== undefined && years.includes(options.year) ? options.year : "all";

  const filtered =
    activeYear === "all" ? base : await fetchAllFlyers(activeYear);
  const pastDtos = filtered.items.filter((dto) => dto.id !== currentDto?.id);

  return {
    currentFlyer,
    pastFlyers: pastDtos.map((dto) => mapFlyerSummary(dto)),
    totalFlyerCount: base.total,
    years,
    activeYear,
  };
}

/** Loads a single flyer for `/flyers/[slug]`. Throws `FlyerNotFoundError` on a 404. */
export async function getFlyerDetail(slug: string): Promise<FlyerArchiveItem> {
  const dto = await fetchFlyerBySlug(slug);
  return mapFlyerSummary(dto);
}

const FLYER_PRODUCTS_PAGE_SIZE = 100;

/** Loads and maps all product-card observations for one flyer. */
export async function getFlyerProducts(slug: string): Promise<FlyerProductCard[]> {
  const firstPage = await fetchFlyerProducts(slug, {
    page: 1,
    page_size: FLYER_PRODUCTS_PAGE_SIZE,
  });
  if (
    firstPage.page !== 1 ||
    firstPage.page_size !== FLYER_PRODUCTS_PAGE_SIZE
  ) {
    throw new FlyerApiError("Flyer API returned inconsistent flyer products pagination.");
  }
  const items = [...firstPage.items];
  const pageCount = Math.ceil(firstPage.total / firstPage.page_size);

  for (let page = 2; page <= pageCount; page += 1) {
    const nextPage = await fetchFlyerProducts(slug, {
      page,
      page_size: firstPage.page_size,
    });
    if (
      nextPage.page !== page ||
      nextPage.page_size !== firstPage.page_size ||
      nextPage.total !== firstPage.total
    ) {
      throw new FlyerApiError("Flyer API returned inconsistent flyer products pagination.");
    }
    items.push(...nextPage.items);
  }

  if (items.length !== firstPage.total) {
    throw new FlyerApiError("Flyer API returned an incomplete flyer products result.");
  }

  return items.map((item) => ({
    id: item.id,
    cardIndex: item.card_index,
    page: item.page,
    brand: item.brand,
    name: item.name,
    description: item.description,
    quantity: item.quantity,
    price: item.price,
    referencePrice: item.reference_price,
    unitPrices: item.unit_prices.map((unitPrice) => ({
      value: unitPrice.value,
      unit: unitPrice.unit,
      basis: unitPrice.basis,
      perUnit: unitPrice.per_unit,
      raw: unitPrice.raw,
    })),
    discountPercent: item.discount_percent,
    lidlPlus: item.lidl_plus,
    currency: item.currency,
    status: item.status,
    parserVersion: item.parser_version,
    warnings: item.warnings,
    notes: item.notes,
  }));
}
