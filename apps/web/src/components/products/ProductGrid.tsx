import type { Product } from "@/lib/products";

import { ProductCard } from "./ProductCard";

/**
 * Mobile-first responsive grid.
 *
 * Single column only on very narrow phones, two columns from ~360px (keeps
 * cards scannable instead of one huge tile per screen), then three and four on
 * larger screens so cards never stretch out of proportion.
 */
export function ProductGrid({ products }: { products: Product[] }) {
  if (products.length === 0) {
    return (
      <div className="rounded-[var(--radius-card)] border border-dashed border-line-strong bg-surface p-10 text-center">
        <p className="text-sm font-semibold text-ink">No products found</p>
        <p className="mt-1 text-sm text-ink-muted">
          Try a different search term or clear the filters.
        </p>
      </div>
    );
  }

  return (
    <ul
      role="list"
      className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-4 lg:grid-cols-3 lg:gap-5 xl:grid-cols-4"
    >
      {products.map((product) => (
        <li key={product.id} className="h-full">
          <ProductCard product={product} />
        </li>
      ))}
    </ul>
  );
}
