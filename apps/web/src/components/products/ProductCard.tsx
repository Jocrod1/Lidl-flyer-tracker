import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { formatLastSeen, formatPrice, type Product } from "@/lib/products";

import { ProductImage } from "./ProductImage";

/**
 * Presentational product tile. Receives everything it needs as props — no data
 * fetching here, so the grid can be fed from mock data today and an API later.
 */
export function ProductCard({ product }: { product: Product }) {
  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-line-strong hover:shadow-md focus-within:border-brand">
      <div className="relative">
        <ProductImage
          shape={product.image.shape}
          tint={product.image.tint}
          className="aspect-[4/3] w-full"
        />
        <div className="absolute left-3 top-3">
          <Badge>{product.category}</Badge>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-1 p-3 sm:p-4">
        <p className="text-[0.6875rem] font-bold uppercase tracking-[0.1em] text-brand">
          {product.brand}
        </p>

        <h3 className="text-pretty text-sm font-semibold leading-snug text-ink sm:text-[0.9375rem]">
          <Link
            href={`/products/${product.slug}`}
            title={product.name}
            className="line-clamp-3 rounded-sm before:absolute before:inset-0 before:content-['']"
          >
            {product.name}
          </Link>
        </h3>

        <div className="mt-auto flex items-end justify-between gap-3 pt-3">
          <span className="min-w-0 truncate text-sm text-ink-muted">
            {product.quantity}
          </span>
          <span className="shrink-0 text-lg font-bold tabular-nums tracking-tight text-ink">
            {formatPrice(product.price)}
          </span>
        </div>

        <p className="mt-3 border-t border-line pt-3 text-xs text-ink-subtle">
          Last seen{" "}
          <span aria-hidden="true" className="px-0.5">
            ·
          </span>
          <time dateTime={product.lastSeen} className="font-medium text-ink-muted">
            {formatLastSeen(product.lastSeen)}
          </time>
        </p>
      </div>
    </article>
  );
}
