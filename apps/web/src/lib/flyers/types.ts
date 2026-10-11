/**
 * Frontend view model for a flyer. The API uses a different, snake_case
 * response contract; `mapper.ts` converts it here so presentation components
 * remain independent of transport details.
 */

export interface FlyerArchiveItem {
  /** Stable identifier converted to a string from the API's integer id. */
  id: string;
  /** URL-safe identifier used for /flyers/[slug]. */
  slug: string;
  title: string;
  /** ISO date (YYYY-MM-DD) the flyer went live, or empty when absent. */
  dateFrom: string;
  /** ISO date (YYYY-MM-DD) the flyer expires, or empty when absent. */
  dateTo: string;
  /** Number of products captured from this flyer. */
  productCount: number;
  /** Generated tint placeholder; the API does not currently provide artwork. */
  coverImage: string;
  /** Whether this is the first flyer in the API's newest-first list. */
  isCurrent?: boolean;
}
