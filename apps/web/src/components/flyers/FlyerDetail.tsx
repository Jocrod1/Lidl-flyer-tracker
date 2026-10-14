import Link from "next/link";

import { FlyerCover } from "@/components/flyers/FlyerCover";
import { ProductGrid } from "@/components/products/ProductGrid";
import { Container } from "@/components/ui/Container";
import { formatDateRange, type FlyerArchiveItem } from "@/lib/flyers";
import type { FlyerProductCard } from "@/lib/products";

/**
 * Screen composition for Flyer Detail (`/flyers/[slug]`).
 *
 * Keeps flyer-specific card observations in the existing product-card
 * presentation without treating them as canonical products.
 */
export function FlyerDetail({
  flyer,
  products,
  productsError,
}: {
  flyer: FlyerArchiveItem;
  products: FlyerProductCard[];
  productsError: boolean;
}) {
  const metadata = [
    { label: "Valid from", value: formatDateRange(flyer.dateFrom, flyer.dateTo) },
    { label: "Products tracked", value: String(flyer.productCount) },
  ];

  return (
    <Container className="py-8 sm:py-10">
      <div className="mb-6 sm:mb-8">
        <Link
          href="/flyers"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink sm:hidden"
        >
          <span aria-hidden="true">←</span> Back to archive
        </Link>

        <nav aria-label="Breadcrumb" className="hidden sm:block">
          <ol className="flex items-center gap-1.5 text-sm text-ink-muted">
            <li>
              <Link href="/flyers" className="hover:text-ink">
                Flyer Archive
              </Link>
            </li>
            <li aria-hidden="true" className="text-ink-subtle">
              /
            </li>
            <li className="max-w-sm truncate font-medium text-ink" aria-current="page">
              {flyer.title}
            </li>
          </ol>
        </nav>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 sm:items-start sm:gap-10 lg:gap-14">
        <FlyerCover
          tint={flyer.coverImage}
          className="aspect-square w-full rounded-[var(--radius-card)] border border-line sm:aspect-[4/5]"
        />

        <div className="flex flex-col gap-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-brand">
              {formatDateRange(flyer.dateFrom, flyer.dateTo)}
            </p>
            <h1 className="mt-1 text-pretty text-2xl font-bold leading-tight tracking-tight text-ink sm:text-3xl">
              {flyer.title}
            </h1>
          </div>

          <p className="border-t border-line pt-4 text-sm text-ink-muted">
            <strong className="font-semibold text-ink">{flyer.productCount}</strong>{" "}
            products tracked from this flyer.
          </p>
        </div>
      </div>

      <section className="mt-12 border-t border-line pt-8 sm:mt-16">
        <h2 className="text-[0.6875rem] font-bold uppercase tracking-[0.1em] text-ink-subtle">
          Flyer details
        </h2>
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4">
          {metadata.map((item) => (
            <div key={item.label}>
              <dt className="text-xs text-ink-subtle">{item.label}</dt>
              <dd className="mt-0.5 text-sm font-medium text-ink">{item.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-12 sm:mt-16">
        <h2 className="text-lg font-bold tracking-tight text-ink sm:text-xl">
          Products in this flyer
        </h2>
        {productsError ? (
          <div
            role="status"
            className="mt-5 rounded-[var(--radius-card)] border border-dashed border-line-strong bg-surface p-10 text-center"
          >
            <p className="text-sm font-semibold text-ink">
              We couldn&apos;t load this flyer&apos;s product cards
            </p>
            <p className="mt-1 text-sm text-ink-muted">
              The Flyer API might be unavailable right now. Please try again
              later or return to the{" "}
              <Link
                href="/flyers"
                className="font-medium text-brand hover:text-brand-strong"
              >
                flyer archive
              </Link>
              .
            </p>
          </div>
        ) : (
          <div className="mt-5">
            <ProductGrid
              products={products}
              emptyState={{
                title: "No product cards in this flyer",
                description: "There are no extracted product cards to show yet.",
              }}
            />
          </div>
        )}
      </section>
    </Container>
  );
}
