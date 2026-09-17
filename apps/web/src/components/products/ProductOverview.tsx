import { Badge } from "@/components/ui/Badge";
import { formatLastSeen, formatPrice, type ProductDetail } from "@/lib/products";

import { ProductImage } from "./ProductImage";

/**
 * Product overview: image + core facts.
 *
 * Two columns on larger screens (image left, info right), stacked with the
 * image first on mobile. No purchase affordances — this is a research view.
 */
export function ProductOverview({ product }: { product: ProductDetail }) {
  return (
    <div className="grid gap-6 sm:grid-cols-2 sm:items-start sm:gap-10 lg:gap-14">
      <ProductImage
        shape={product.image.shape}
        tint={product.image.tint}
        className="aspect-square w-full rounded-[var(--radius-card)] border border-line sm:aspect-[4/5]"
      />

      <div className="flex flex-col gap-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-brand">
            {product.brand}
          </p>
          <h1 className="mt-1 text-pretty text-2xl font-bold leading-tight tracking-tight text-ink sm:text-3xl">
            {product.name}
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="brand">{product.category}</Badge>
          <span className="text-sm text-ink-muted">{product.quantity}</span>
        </div>

        <p className="text-4xl font-bold tabular-nums tracking-tight text-ink">
          {formatPrice(product.price)}
        </p>

        <p className="border-t border-line pt-4 text-sm text-ink-muted">
          Last seen{" "}
          <time dateTime={product.lastSeen} className="font-medium text-ink">
            {formatLastSeen(product.lastSeen)}
          </time>
        </p>
      </div>
    </div>
  );
}
