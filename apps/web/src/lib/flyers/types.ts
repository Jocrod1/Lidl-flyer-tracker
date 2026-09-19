/**
 * Flyer domain types.
 *
 * Mirrors the shape we expect the ingestion backend to eventually expose for
 * the Flyer Archive, so swapping `getFlyers()`/`getFlyer()` for a real fetch
 * later should not require touching the presentation components.
 */

export interface FlyerArchiveItem {
  /** Stable identifier from the ingestion database. */
  id: string;
  /** URL-safe identifier used for /flyers/[slug]. */
  slug: string;
  title: string;
  /** ISO date (YYYY-MM-DD) the flyer went live. */
  dateFrom: string;
  /** ISO date (YYYY-MM-DD) the flyer expires. */
  dateTo: string;
  /** Number of products captured from this flyer. */
  productCount: number;
  /** Reference to flyer cover artwork. Not a remote image — see `FlyerCover`. */
  coverImage: string;
  /** Whether this is the most recent flyer in the archive. */
  isCurrent?: boolean;
}
