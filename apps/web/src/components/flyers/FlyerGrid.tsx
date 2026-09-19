import type { FlyerArchiveItem } from "@/lib/flyers";

import { FlyerCard } from "./FlyerCard";

/**
 * Mobile-first responsive grid, matching `ProductGrid`'s breakpoints so the
 * archive and the explorer feel like the same layout system.
 */
export function FlyerGrid({ flyers }: { flyers: FlyerArchiveItem[] }) {
  if (flyers.length === 0) {
    return (
      <div className="rounded-[var(--radius-card)] border border-dashed border-line-strong bg-surface p-10 text-center">
        <p className="text-sm font-semibold text-ink">No flyers found</p>
        <p className="mt-1 text-sm text-ink-muted">
          Try a different year.
        </p>
      </div>
    );
  }

  return (
    <ul
      role="list"
      className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-4 lg:grid-cols-3 lg:gap-5 xl:grid-cols-4"
    >
      {flyers.map((flyer) => (
        <li key={flyer.id} className="h-full">
          <FlyerCard flyer={flyer} />
        </li>
      ))}
    </ul>
  );
}
