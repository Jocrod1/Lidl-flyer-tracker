import type { FlyerArchiveItem } from "./types";

/**
 * Local mock dataset standing in for the ingestion backend.
 *
 * Replace `getFlyers()` with a real fetch later — the UI only depends on the
 * `FlyerArchiveItem` shape and never fetches anything itself. `id` follows the
 * same `flyer-<year>-w<week>` convention used by `ProductAppearance.flyerId`
 * in `lib/products`, so the two datasets stay linkable once a real backend
 * joins them.
 *
 * Ordered most recent first; `FLYERS[0]` is treated as the current flyer.
 */
const FLYERS: FlyerArchiveItem[] = [
  {
    id: "flyer-2026-w37",
    slug: "semana-37-2026",
    title: "Week 37 flyer",
    dateFrom: "2026-09-07",
    dateTo: "2026-09-13",
    productCount: 214,
    coverImage: "#0050aa",
    isCurrent: true,
  },
  {
    id: "flyer-2026-w36",
    slug: "semana-36-2026",
    title: "Week 36 flyer",
    dateFrom: "2026-08-31",
    dateTo: "2026-09-06",
    productCount: 208,
    coverImage: "#3f72c4",
  },
  {
    id: "flyer-2026-w35",
    slug: "semana-35-2026",
    title: "Week 35 flyer",
    dateFrom: "2026-08-24",
    dateTo: "2026-08-30",
    productCount: 197,
    coverImage: "#4f8de0",
  },
  {
    id: "flyer-2026-w34",
    slug: "semana-34-2026",
    title: "Week 34 flyer",
    dateFrom: "2026-08-17",
    dateTo: "2026-08-23",
    productCount: 203,
    coverImage: "#7aa7e8",
  },
  {
    id: "flyer-2026-w33",
    slug: "semana-33-2026",
    title: "Week 33 flyer",
    dateFrom: "2026-08-10",
    dateTo: "2026-08-16",
    productCount: 191,
    coverImage: "#0050aa",
  },
  {
    id: "flyer-2026-w32",
    slug: "semana-32-2026",
    title: "Week 32 flyer",
    dateFrom: "2026-08-03",
    dateTo: "2026-08-09",
    productCount: 205,
    coverImage: "#3f72c4",
  },
  {
    id: "flyer-2026-w31",
    slug: "semana-31-2026",
    title: "Week 31 flyer",
    dateFrom: "2026-07-27",
    dateTo: "2026-08-02",
    productCount: 199,
    coverImage: "#4f8de0",
  },
  {
    id: "flyer-2026-w30",
    slug: "semana-30-2026",
    title: "Week 30 flyer",
    dateFrom: "2026-07-20",
    dateTo: "2026-07-26",
    productCount: 188,
    coverImage: "#7aa7e8",
  },
  {
    id: "flyer-2026-w29",
    slug: "semana-29-2026",
    title: "Week 29 flyer",
    dateFrom: "2026-07-13",
    dateTo: "2026-07-19",
    productCount: 212,
    coverImage: "#0050aa",
  },
  {
    id: "flyer-2026-w28",
    slug: "semana-28-2026",
    title: "Week 28 flyer",
    dateFrom: "2026-07-06",
    dateTo: "2026-07-12",
    productCount: 196,
    coverImage: "#3f72c4",
  },
];

/** All archived flyers, most recent first. */
export function getFlyers(): FlyerArchiveItem[] {
  return FLYERS;
}

/** The most recent flyer, highlighted at the top of the archive. */
export function getCurrentFlyer(): FlyerArchiveItem {
  return FLYERS.find((flyer) => flyer.isCurrent) ?? FLYERS[0];
}

/** Every previous flyer, most recent first — excludes the current flyer. */
export function getPastFlyers(): FlyerArchiveItem[] {
  return FLYERS.filter((flyer) => !flyer.isCurrent);
}

/** Every known flyer slug, for `generateStaticParams()`. */
export function getFlyerSlugs(): string[] {
  return FLYERS.map((flyer) => flyer.slug);
}

/** Looks up a single flyer by slug, or `undefined` if it doesn't exist. */
export function getFlyer(slug: string): FlyerArchiveItem | undefined {
  return FLYERS.find((flyer) => flyer.slug === slug);
}

/** Distinct years present in the archive, newest first — powers the year filter. */
export function getFlyerYears(): number[] {
  const years = new Set(FLYERS.map((flyer) => Number(flyer.dateFrom.slice(0, 4))));
  return Array.from(years).sort((a, b) => b - a);
}
