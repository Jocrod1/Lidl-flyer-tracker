import Link from "next/link";

import { Container } from "@/components/ui/Container";
import { formatLastSeen, type ProductDetail as ProductDetailData } from "@/lib/products";

import { AppearanceTimeline } from "./AppearanceTimeline";
import { PriceHistory } from "./PriceHistory";
import { ProductOverview } from "./ProductOverview";

/**
 * Screen composition for Product Detail (`/products/[slug]`).
 *
 * Receives an already-resolved `ProductDetail` record, so the page above it
 * owns data access (and the `notFound()` call) and this stays a pure
 * presentation layer, matching the Product Explorer's pattern.
 */
export function ProductDetail({ product }: { product: ProductDetailData }) {
  const metadata = [
    { label: "Category", value: product.category },
    { label: "Brand", value: product.brand },
    { label: "Quantity", value: product.quantity },
    { label: "First seen", value: formatLastSeen(product.firstSeen) },
    { label: "Last seen", value: formatLastSeen(product.lastSeen) },
    { label: "Appearances", value: String(product.appearanceCount) },
  ];

  return (
    <Container className="py-8 sm:py-10">
      <div className="mb-6 sm:mb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink sm:hidden"
        >
          <span aria-hidden="true">←</span> Back to products
        </Link>

        <nav aria-label="Breadcrumb" className="hidden sm:block">
          <ol className="flex items-center gap-1.5 text-sm text-ink-muted">
            <li>
              <Link href="/" className="hover:text-ink">
                Products
              </Link>
            </li>
            <li aria-hidden="true" className="text-ink-subtle">
              /
            </li>
            <li className="max-w-sm truncate font-medium text-ink" aria-current="page">
              {product.name}
            </li>
          </ol>
        </nav>
      </div>

      <ProductOverview product={product} />

      <section className="mt-12 sm:mt-16">
        <h2 className="text-lg font-bold tracking-tight text-ink sm:text-xl">
          Price history
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          How the flyer price has moved over time.
        </p>
        <div className="mt-5 rounded-[var(--radius-card)] border border-line bg-surface p-4 sm:p-6">
          <PriceHistory
            priceHistory={product.priceHistory}
            referencePrice={product.referencePrice}
          />
        </div>
      </section>

      <section className="mt-12 sm:mt-16">
        <h2 className="text-lg font-bold tracking-tight text-ink sm:text-xl">
          Appearance history
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          Every flyer this product has appeared in.
        </p>
        <div className="mt-5">
          <AppearanceTimeline appearances={product.appearances} />
        </div>
      </section>

      <section className="mt-12 border-t border-line pt-8 sm:mt-16">
        <h2 className="text-[0.6875rem] font-bold uppercase tracking-[0.1em] text-ink-subtle">
          Product details
        </h2>
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
          {metadata.map((item) => (
            <div key={item.label}>
              <dt className="text-xs text-ink-subtle">{item.label}</dt>
              <dd className="mt-0.5 text-sm font-medium text-ink">{item.value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </Container>
  );
}
