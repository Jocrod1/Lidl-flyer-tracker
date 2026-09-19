import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { formatDateRange, type FlyerArchiveItem } from "@/lib/flyers";

import { FlyerCover } from "./FlyerCover";

/**
 * Highlight card for the current/latest flyer.
 *
 * Visually distinct from `FlyerCard` (larger cover, brand-tinted border, two
 * CTAs) but built from the same tokens — card radius, borders, badges, and
 * button treatment all match Product Detail.
 */
export function FeaturedFlyer({ flyer }: { flyer: FlyerArchiveItem }) {
  return (
    <section
      aria-label="Current flyer"
      className="overflow-hidden rounded-[var(--radius-card)] border border-brand/20 bg-surface shadow-sm sm:grid sm:grid-cols-2"
    >
      <FlyerCover tint={flyer.coverImage} className="aspect-[16/9] w-full sm:aspect-auto sm:h-full" />

      <div className="flex flex-col gap-4 p-5 sm:p-8">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="brand">Current flyer</Badge>
          <span className="text-sm text-ink-muted">
            {formatDateRange(flyer.dateFrom, flyer.dateTo)}
          </span>
        </div>

        <h2 className="text-pretty text-2xl font-bold leading-tight tracking-tight text-ink sm:text-3xl">
          {flyer.title}
        </h2>

        <p className="text-sm text-ink-muted">
          <strong className="font-semibold text-ink">{flyer.productCount}</strong>{" "}
          products tracked from this flyer.
        </p>

        <div className="mt-auto flex flex-wrap gap-3 pt-2">
          <Link
            href={`/flyers/${flyer.slug}`}
            className="inline-flex h-11 items-center justify-center rounded-lg bg-brand px-5 text-sm font-semibold text-white transition-colors hover:bg-brand-strong"
          >
            View flyer
          </Link>
          <Link
            href="/"
            className="inline-flex h-11 items-center justify-center rounded-lg border border-line px-5 text-sm font-semibold text-ink transition-colors hover:border-line-strong hover:bg-surface-sunken"
          >
            Browse products
          </Link>
        </div>
      </div>
    </section>
  );
}
