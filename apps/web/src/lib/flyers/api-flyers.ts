import {
  FlyerApiError,
  fetchFlyerBySlug,
  fetchFlyerList,
  type FlyerSummaryDTO,
} from "./api";
import { mapFlyerSummary } from "./mapper";
import type { FlyerArchiveItem } from "./types";

export { FlyerApiError, FlyerNotFoundError, MissingApiBaseUrlError } from "./api";

/**
 * Page size used when loading the archive to compute year facets, the
 * current flyer, and the total count.
 *
 * The archive is small today (a handful of flyers ingested so far — see
 * the root README's ingestion results table), so one page covers the
 * whole thing and there is no need for real pagination UI yet. This is
 * the API's enforced maximum (`MAX_PAGE_SIZE` in
 * `apps/api/src/api/routers/flyers.py`). If the archive outgrows this,
 * `getFlyerArchive` will need to paginate for real — see
 * docs/backend-frontend-integration-plan.md Phase 2 pagination notes.
 */
const ARCHIVE_PAGE_SIZE = 100;

/** Thrown when the API has no flyers at all — an edge case the old mock data never hit. */
export class FlyerArchiveEmptyError extends FlyerApiError {
  constructor() {
    super("No flyers have been ingested yet.");
    this.name = "FlyerArchiveEmptyError";
  }
}

export interface FlyerArchivePage {
  currentFlyer: FlyerArchiveItem;
  pastFlyers: FlyerArchiveItem[];
  totalFlyerCount: number;
  years: number[];
  activeYear: number | "all";
}

function distinctYears(items: FlyerSummaryDTO[]): number[] {
  const years = new Set<number>();
  for (const item of items) {
    if (item.start_date) {
      years.add(Number(item.start_date.slice(0, 4)));
    }
  }
  return Array.from(years).sort((a, b) => b - a);
}

/**
 * Loads everything the Flyer Archive (`/flyers`) page needs in one call.
 *
 * Always fetches the unfiltered archive first (to resolve the current
 * flyer, the year facets, and the total count), then — only when
 * `year` is a real, present year — makes a second request with
 * `?year=` so the year filter maps directly onto the real API query
 * param rather than being reproduced client-side.
 */
export async function getFlyerArchive(
  options: { year?: number } = {},
): Promise<FlyerArchivePage> {
  const base = await fetchFlyerList({ page: 1, page_size: ARCHIVE_PAGE_SIZE });

  if (base.items.length === 0) {
    throw new FlyerArchiveEmptyError();
  }

  const years = distinctYears(base.items);
  const currentDto = base.items[0];
  const currentFlyer = mapFlyerSummary(currentDto, { isCurrent: true });

  const activeYear: number | "all" =
    options.year !== undefined && years.includes(options.year) ? options.year : "all";

  const pastDtos =
    activeYear === "all"
      ? base.items.filter((dto) => dto.id !== currentDto.id)
      : (await fetchFlyerList({ page: 1, page_size: ARCHIVE_PAGE_SIZE, year: activeYear })).items.filter(
          (dto) => dto.id !== currentDto.id,
        );

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
