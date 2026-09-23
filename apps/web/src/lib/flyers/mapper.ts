import type { FlyerSummaryDTO } from "./api";
import type { FlyerArchiveItem } from "./types";

/**
 * Cover tints cycled by flyer id — mirrors the rotation the old mock
 * dataset used by hand. The backend does not expose flyer cover artwork
 * yet (see docs/backend-frontend-integration-plan.md Phase 5), so this
 * keeps `FlyerCover`'s generated-placeholder look stable per flyer
 * without needing a real image.
 */
const COVER_TINTS = ["#0050aa", "#3f72c4", "#4f8de0", "#7aa7e8"] as const;

function tintForFlyerId(id: number): string {
  return COVER_TINTS[Math.abs(id) % COVER_TINTS.length];
}

/**
 * Maps one API flyer DTO onto the frontend's `FlyerArchiveItem` type, so
 * components never see backend field names (snake_case, nullable dates,
 * numeric ids) — only the shape they already know.
 */
export function mapFlyerSummary(
  dto: FlyerSummaryDTO,
  options: { isCurrent?: boolean } = {},
): FlyerArchiveItem {
  return {
    id: String(dto.id),
    slug: dto.slug,
    title: dto.name || dto.category || `Flyer #${dto.id}`,
    // start_date/end_date are nullable TEXT columns in Postgres (see
    // migrations/001_create_flyers.sql). Missing dates fall back to an
    // empty string; `formatDateRange` renders a friendly placeholder
    // rather than crashing on an unparsable date.
    dateFrom: dto.start_date ?? "",
    dateTo: dto.end_date ?? "",
    productCount: dto.product_count,
    coverImage: tintForFlyerId(dto.id),
    isCurrent: options.isCurrent,
  };
}
