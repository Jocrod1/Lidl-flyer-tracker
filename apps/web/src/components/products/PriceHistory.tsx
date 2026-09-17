import {
  formatLastSeen,
  formatMonthLabel,
  formatPrice,
  type PriceHistoryPoint,
} from "@/lib/products";

/**
 * Price-history chart.
 *
 * A small SVG line chart — no charting library. `priceHistory` is a plain
 * `{ date, price }[]` (oldest first) so a real API can replace the mock
 * generator without this component changing at all.
 */
export function PriceHistory({
  priceHistory,
  referencePrice,
}: {
  priceHistory: PriceHistoryPoint[];
  referencePrice: number | null;
}) {
  if (priceHistory.length === 0) {
    return (
      <p className="text-sm text-ink-muted">No price history recorded yet.</p>
    );
  }

  const width = 640;
  const height = 220;
  const padding = { top: 28, right: 20, bottom: 28, left: 16 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const prices = priceHistory.map((point) => point.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceSpan = maxPrice - minPrice || 1;

  const dates = priceHistory.map((point) => Date.parse(point.date));
  const minDate = Math.min(...dates);
  const maxDate = Math.max(...dates);
  const dateSpan = maxDate - minDate || 1;

  const points = priceHistory.map((point, index) => {
    const timestamp = dates[index];
    const x =
      priceHistory.length === 1
        ? padding.left + plotWidth / 2
        : padding.left + ((timestamp - minDate) / dateSpan) * plotWidth;
    const y =
      padding.top + (1 - (point.price - minPrice) / priceSpan) * plotHeight;
    return { ...point, x, y };
  });

  const linePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"}${point.x},${point.y}`)
    .join(" ");

  const latest = points[points.length - 1];

  return (
    <div>
      {referencePrice ? (
        <p className="mb-4 text-sm text-ink-muted">
          Historical high{" "}
          <span className="font-semibold text-ink">
            {formatPrice(referencePrice)}
          </span>
        </p>
      ) : null}

      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Price history from ${formatLastSeen(
          priceHistory[0].date,
        )} to ${formatLastSeen(priceHistory[priceHistory.length - 1].date)}`}
        className="h-auto w-full overflow-visible"
      >
        <line
          x1={padding.left}
          y1={height - padding.bottom}
          x2={width - padding.right}
          y2={height - padding.bottom}
          stroke="var(--line)"
        />

        <path d={linePath} fill="none" stroke="var(--brand)" strokeWidth={2} />

        {points.map((point, index) => {
          const isLatest = index === points.length - 1;
          return (
            <g key={point.date}>
              <circle
                cx={point.x}
                cy={point.y}
                r={isLatest ? 5 : 4}
                fill={isLatest ? "var(--brand)" : "var(--surface)"}
                stroke="var(--brand)"
                strokeWidth={2}
              />
              <text
                x={point.x}
                y={point.y - 14}
                textAnchor="middle"
                className="fill-ink text-[11px] font-semibold"
              >
                {formatPrice(point.price)}
              </text>
              <text
                x={point.x}
                y={height - padding.bottom + 18}
                textAnchor="middle"
                className="fill-ink-subtle text-[10px] font-medium uppercase tracking-wide"
              >
                {formatMonthLabel(point.date)}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Accessible, non-visual data table backing the chart above. */}
      <table className="sr-only">
        <caption>Price history</caption>
        <thead>
          <tr>
            <th>Date</th>
            <th>Price</th>
          </tr>
        </thead>
        <tbody>
          {priceHistory.map((point) => (
            <tr key={point.date}>
              <td>{formatLastSeen(point.date)}</td>
              <td>{formatPrice(point.price)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mt-3 text-xs text-ink-subtle">
        Currently {formatPrice(latest.price)} · last recorded{" "}
        {formatLastSeen(latest.date)}
      </p>
    </div>
  );
}
