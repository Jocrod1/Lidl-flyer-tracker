import {
  formatLastSeen,
  formatPrice,
  type ProductAppearance,
} from "@/lib/products";

/**
 * Flyer appearance timeline, most recent first.
 *
 * Each row is structured to become a link to a Flyer Detail page later
 * (`flyerId`/`flyerName` are already present) without changing this markup —
 * for now the rows are static, since that screen doesn't exist yet.
 */
export function AppearanceTimeline({
  appearances,
}: {
  appearances: ProductAppearance[];
}) {
  if (appearances.length === 0) {
    return (
      <p className="text-sm text-ink-muted">No flyer appearances recorded yet.</p>
    );
  }

  return (
    <ol className="relative border-l border-line pl-6">
      {appearances.map((appearance) => (
        <li key={appearance.flyerId} className="relative pb-7 last:pb-0">
          <span
            aria-hidden="true"
            className="absolute -left-[29px] top-1 h-3 w-3 rounded-full border-2 border-brand bg-surface"
          />
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <time dateTime={appearance.date} className="text-sm font-semibold text-ink">
              {formatLastSeen(appearance.date)}
            </time>
            <span className="text-base font-bold tabular-nums text-ink">
              {formatPrice(appearance.price)}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-ink-subtle">
            Flyer <span aria-hidden="true">·</span> {appearance.flyerName}
          </p>
        </li>
      ))}
    </ol>
  );
}
