/**
 * Product domain types.
 *
 * These mirror the shape we expect the ingestion backend to eventually expose,
 * so swapping `getProducts()` for an API call should not require touching the
 * presentation components.
 */

export type ProductCategory =
  | "Dairy"
  | "Bakery"
  | "Meat & Fish"
  | "Fruit & Veg"
  | "Pantry"
  | "Drinks"
  | "Frozen"
  | "Household";

/**
 * Silhouette used by the generated placeholder artwork. Real flyer imagery is
 * not available yet, so each product declares the packaging shape it should be
 * drawn as. Once `imageUrl` is populated by the backend, this becomes the
 * fallback only.
 */
export type PackagingShape =
  | "bottle"
  | "carton"
  | "block"
  | "jar"
  | "box"
  | "bag"
  | "tray"
  | "can"
  | "loaf"
  | "tub";

export interface Product {
  /** Stable identifier from the ingestion database. */
  id: string;
  /** URL-safe identifier used for /products/[slug]. */
  slug: string;
  brand: string;
  name: string;
  /** Pack size exactly as printed in the flyer, e.g. "1,2 kg" or "6 x 33 cl". */
  quantity: string;
  /** Price in euros. */
  price: number;
  category: ProductCategory;
  /** ISO date (YYYY-MM-DD) of the most recent flyer this product appeared in. */
  lastSeen: string;
  /** Remote product image. Null until the ingestion pipeline captures one. */
  imageUrl: string | null;
  /** Placeholder artwork hints, used while `imageUrl` is null. */
  image: {
    shape: PackagingShape;
    /** Base hue of the generated artwork, as a hex colour. */
    tint: string;
  };
}

/**
 * A single flyer this product appeared in.
 *
 * `flyerId` is intentionally already shaped like a routable identifier so the
 * Product Detail timeline can link straight to `/flyers/[flyerId]` once the
 * Flyer Archive/Detail screens exist, without changing this type.
 */
export interface ProductAppearance {
  /** ISO date (YYYY-MM-DD) the flyer went live. */
  date: string;
  /** Price shown in that flyer. */
  price: number;
  flyerId: string;
  /** Human-readable flyer label, e.g. "Week 34". */
  flyerName: string;
}

/** A single point on the price-history chart, oldest first. */
export interface PriceHistoryPoint {
  /** ISO date (YYYY-MM-DD). */
  date: string;
  price: number;
}

/**
 * Full detail record for a single product page.
 *
 * Extends the Product Explorer's `Product` summary with everything
 * `/products/[slug]` needs. Kept separate from `Product` so the explorer grid
 * never has to fetch history it doesn't render.
 */
export interface ProductDetail extends Product {
  /** ISO date (YYYY-MM-DD) of the earliest known flyer appearance. */
  firstSeen: string;
  /** Total number of recorded flyer appearances. */
  appearanceCount: number;
  /** Flyer appearances, most recent first. */
  appearances: ProductAppearance[];
  /** Price history, oldest first — ready to plot directly. */
  priceHistory: PriceHistoryPoint[];
  /** Highest historical price, when meaningfully above the current price. */
  referencePrice: number | null;
}
