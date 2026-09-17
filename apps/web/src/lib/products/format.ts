const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

/**
 * Formats a price the way it is printed in Spanish flyers: `2,99 €`.
 * Implemented without `Intl` so server and client renders always agree.
 */
export function formatPrice(price: number): string {
  return `${price.toFixed(2).replace(".", ",")} €`;
}

/** Formats an ISO date (YYYY-MM-DD) as `21 Aug 2026`. */
export function formatLastSeen(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  const monthIndex = Number(month) - 1;
  const monthLabel = MONTHS[monthIndex] ?? month;
  return `${Number(day)} ${monthLabel} ${year}`;
}

/** Formats an ISO date (YYYY-MM-DD) as the short month label `Aug`, for chart axes. */
export function formatMonthLabel(isoDate: string): string {
  const monthIndex = Number(isoDate.split("-")[1]) - 1;
  return MONTHS[monthIndex] ?? isoDate;
}
