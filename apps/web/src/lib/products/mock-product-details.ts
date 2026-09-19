import { getProducts } from "./mock-products";
import type { Product, ProductAppearance, ProductDetail } from "./types";

/**
 * Mock Product Detail dataset.
 *
 * Derives realistic-looking flyer appearance and price history for each
 * product from the Product Explorer's summary data, using a seeded
 * pseudo-random generator so results are stable across renders/builds.
 *
 * This is the only place that knows the detail data is fabricated —
 * `getProductDetail()` is the seam to swap for a real API/database call
 * later, and every consumer only depends on the `ProductDetail` shape.
 */

/** Small deterministic PRNG (Park-Miller) seeded per product id. */
function createRandom(seed: number): () => number {
  let state = seed % 2147483647;
  if (state <= 0) state += 2147483646;
  return () => {
    state = (state * 16807) % 2147483647;
    return (state - 1) / 2147483646;
  };
}

function hashSeed(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) | 0;
  }
  return Math.abs(hash) || 1;
}

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** ISO 8601 week number, matching how Lidl flyers are numbered. */
function isoWeekNumber(date: Date): number {
  const target = new Date(
    Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()),
  );
  const dayNumber = target.getUTCDay() || 7;
  target.setUTCDate(target.getUTCDate() + 4 - dayNumber);
  const yearStart = new Date(Date.UTC(target.getUTCFullYear(), 0, 1));
  return Math.ceil(((target.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

function buildAppearances(product: Product): ProductAppearance[] {
  const random = createRandom(hashSeed(product.id));
  const count = 4 + Math.floor(random() * 3); // 4–6 appearances

  const appearances: ProductAppearance[] = [];
  let date = new Date(`${product.lastSeen}T00:00:00Z`);
  let price = product.price;

  for (let i = 0; i < count; i += 1) {
    const week = isoWeekNumber(date);
    appearances.push({
      date: toIsoDate(date),
      price: Math.round(price * 100) / 100,
      flyerId: `flyer-${date.getUTCFullYear()}-w${String(week).padStart(2, "0")}`,
      flyerName: `Week ${week}`,
    });

    // Step back 4–9 weeks for the previous flyer appearance.
    const stepWeeks = 4 + Math.floor(random() * 6);
    const previous = new Date(date);
    previous.setUTCDate(previous.getUTCDate() - stepWeeks * 7);
    date = previous;

    // Historical prices drift a little higher the further back we go.
    const drift = 1 + (random() * 0.14 - 0.02);
    price = Math.round(price * drift * 100) / 100;
  }

  return appearances;
}

const DETAIL_CACHE = new Map<string, ProductDetail>();

function buildDetail(product: Product): ProductDetail {
  const appearances = buildAppearances(product).sort((a, b) =>
    b.date.localeCompare(a.date),
  );
  const chronological = [...appearances].sort((a, b) =>
    a.date.localeCompare(b.date),
  );

  const priceHistory = chronological.map(({ date, price }) => ({ date, price }));
  const highestPrice = Math.max(...priceHistory.map((point) => point.price));

  return {
    ...product,
    firstSeen: chronological[0].date,
    appearanceCount: appearances.length,
    appearances,
    priceHistory,
    referencePrice: highestPrice > product.price ? highestPrice : null,
  };
}

/** Full detail record for a product, or `undefined` for an unknown slug. */
export function getProductDetail(slug: string): ProductDetail | undefined {
  const cached = DETAIL_CACHE.get(slug);
  if (cached) return cached;

  const product = getProducts().find((candidate) => candidate.slug === slug);
  if (!product) return undefined;

  const detail = buildDetail(product);
  DETAIL_CACHE.set(slug, detail);
  return detail;
}

/** All slugs, for static generation of `/products/[slug]`. */
export function getProductSlugs(): string[] {
  return getProducts().map((product) => product.slug);
}
