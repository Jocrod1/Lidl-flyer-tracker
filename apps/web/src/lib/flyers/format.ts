import { formatLastSeen } from "@/lib/products";

/**
 * Formats a flyer's validity window as `7 – 13 Sep 2026`.
 *
 * Falls back to two full dates when the range spans a month or year boundary,
 * e.g. `27 Jul – 2 Aug 2026`.
 */
export function formatDateRange(dateFrom: string, dateTo: string): string {
  if (!dateFrom || !dateTo) {
    // Postgres allows NULL start_date/end_date (see
    // migrations/001_create_flyers.sql) — render a friendly placeholder
    // instead of crashing on an unparsable date.
    return "Dates unavailable";
  }

  const [fromYear, , fromDay] = dateFrom.split("-");
  const [toYear] = dateTo.split("-");

  const toLabel = formatLastSeen(dateTo);

  if (fromYear === toYear) {
    const sameMonth = dateFrom.slice(0, 7) === dateTo.slice(0, 7);
    if (sameMonth) {
      return `${Number(fromDay)} – ${toLabel}`;
    }
    const fromMonthLabel = formatLastSeen(dateFrom).split(" ")[1];
    return `${Number(fromDay)} ${fromMonthLabel} – ${toLabel}`;
  }

  return `${formatLastSeen(dateFrom)} – ${toLabel}`;
}
