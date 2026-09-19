import Link from "next/link";

import { formatDateRange, type FlyerArchiveItem } from "@/lib/flyers";

import { FlyerCover } from "./FlyerCover";

/**
 * Presentational flyer tile for the archive grid. Mirrors `ProductCard`'s
 * structure (image, stretched link, footer meta row) so the two grids feel
 * like the same product.
 */
export function FlyerCard({ flyer }: { flyer: FlyerArchiveItem }) {
  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-line-strong hover:shadow-md focus-within:border-brand">
      <FlyerCover tint={flyer.coverImage} className="aspect-[4/3] w-full" />

      <div className="flex flex-1 flex-col gap-1 p-3 sm:p-4">
        <p className="text-[0.6875rem] font-bold uppercase tracking-[0.1em] text-brand">
          {formatDateRange(flyer.dateFrom, flyer.dateTo)}
        </p>

        <h3 className="text-pretty text-sm font-semibold leading-snug text-ink sm:text-[0.9375rem]">
          <Link
            href={`/flyers/${flyer.slug}`}
            title={flyer.title}
            className="rounded-sm before:absolute before:inset-0 before:content-['']"
          >
            {flyer.title}
          </Link>
        </h3>

        <p className="mt-auto border-t border-line pt-3 text-xs text-ink-subtle">
          <span className="font-medium text-ink-muted">{flyer.productCount}</span>{" "}
          products
        </p>
      </div>
    </article>
  );
}
