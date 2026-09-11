import { Container } from "@/components/ui/Container";

import { SearchBar } from "./SearchBar";

export interface SearchHeroProps {
  productCount: number;
  categoryCount: number;
  /** Human-readable date of the most recent flyer in the archive. */
  latestFlyerLabel: string;
}

export function SearchHero({
  productCount,
  categoryCount,
  latestFlyerLabel,
}: SearchHeroProps) {
  return (
    <section className="relative overflow-hidden border-b border-line bg-surface">
      {/* Soft brand wash, kept low-contrast so the search input stays dominant. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 -top-40 h-80 bg-[radial-gradient(60%_100%_at_50%_100%,var(--brand-soft),transparent)]"
      />

      <Container className="relative">
        <div className="mx-auto max-w-3xl py-10 text-center sm:py-16">
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-ink-muted">
            <span
              aria-hidden="true"
              className="h-1.5 w-1.5 rounded-full bg-highlight"
            />
            Updated weekly
          </span>

          <h1 className="mt-5 text-pretty text-3xl font-bold leading-tight tracking-tight text-ink sm:text-4xl lg:text-5xl">
            Every product from the{" "}
            <span className="relative inline-block whitespace-nowrap text-brand">
              <span
                aria-hidden="true"
                className="absolute inset-x-0 bottom-0.5 h-2 rounded-sm bg-highlight/60"
              />
              <span className="relative">Lidl flyer</span>
            </span>
            , kept on record
          </h1>

          <p className="mx-auto mt-4 max-w-xl text-pretty text-base leading-7 text-ink-muted">
            Lidl Tracker archives the weekly Lidl Spain flyers so you can look up
            a product, check what it cost, and see when it last appeared.
          </p>

          <div className="mt-7 sm:mt-8">
            <SearchBar />
          </div>

          <dl className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-ink-muted">
            <div className="flex items-center gap-1.5">
              <dt className="sr-only">Products tracked</dt>
              <dd>
                <strong className="font-semibold text-ink">
                  {productCount}
                </strong>{" "}
                products tracked
              </dd>
            </div>
            <span aria-hidden="true" className="hidden h-1 w-1 rounded-full bg-line-strong sm:block" />
            <div className="flex items-center gap-1.5">
              <dt className="sr-only">Categories</dt>
              <dd>
                <strong className="font-semibold text-ink">
                  {categoryCount}
                </strong>{" "}
                categories
              </dd>
            </div>
            <span aria-hidden="true" className="hidden h-1 w-1 rounded-full bg-line-strong sm:block" />
            <div className="flex items-center gap-1.5">
              <dt className="sr-only">Latest flyer</dt>
              <dd>
                Latest flyer{" "}
                <strong className="font-semibold text-ink">
                  {latestFlyerLabel}
                </strong>
              </dd>
            </div>
          </dl>
        </div>
      </Container>
    </section>
  );
}
