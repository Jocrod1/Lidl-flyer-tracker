import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import {
  formatLastSeen,
  formatPrice,
  type FlyerProductCard,
  type Product,
} from "@/lib/products";

import { ProductImage } from "./ProductImage";

type ProductCardItem = Product | FlyerProductCard;

/**
 * Presentational product tile. Receives everything it needs as props — no data
 * fetching here. Flyer observations share the card design but do not link to a
 * canonical product because the API does not provide a product identity.
 */
export function ProductCard({ product }: { product: ProductCardItem }) {
  const isFlyerCard = "cardIndex" in product;
  const image = isFlyerCard
    ? { shape: "box" as const, tint: "#4f8de0" }
    : product.image;
  const name = product.name?.trim() || "Name unavailable";
  const quantity = isFlyerCard
    ? product.quantity?.raw.trim() || null
    : product.quantity;
  const flyerPrice =
    isFlyerCard && product.price !== null
      ? product.currency === "EUR"
        ? formatPrice(product.price)
        : `${product.price.toFixed(2)} ${product.currency}`
      : null;

  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-line-strong hover:shadow-md focus-within:border-brand">
      <div className="relative">
        <ProductImage
          shape={image.shape}
          tint={image.tint}
          className="aspect-[4/3] w-full"
        />
        <div className="absolute left-3 top-3">
          {isFlyerCard ? (
            <Badge>{product.status}</Badge>
          ) : (
            <Badge>{product.category}</Badge>
          )}
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-1 p-3 sm:p-4">
        {product.brand && (
          <p className="text-[0.6875rem] font-bold uppercase tracking-[0.1em] text-brand">
            {product.brand}
          </p>
        )}

        <h3 className="text-pretty text-sm font-semibold leading-snug text-ink sm:text-[0.9375rem]">
          {isFlyerCard ? (
            <span className="line-clamp-3">{name}</span>
          ) : (
            <Link
              href={`/products/${product.slug}`}
              title={product.name}
              className="line-clamp-3 rounded-sm before:absolute before:inset-0 before:content-['']"
            >
              {product.name}
            </Link>
          )}
        </h3>

        {isFlyerCard && product.description?.trim() && (
          <p className="text-xs text-ink-muted">{product.description}</p>
        )}

        <div className="mt-auto flex items-end justify-between gap-3 pt-3">
          {quantity && (
            <span className="min-w-0 truncate text-sm text-ink-muted">{quantity}</span>
          )}
          {isFlyerCard ? (
            <span className="shrink-0 text-sm font-semibold text-ink">
              {flyerPrice ?? "Price unavailable"}
            </span>
          ) : (
            <span className="shrink-0 text-lg font-bold tabular-nums tracking-tight text-ink">
              {formatPrice(product.price)}
            </span>
          )}
        </div>

        {isFlyerCard ? (
          <div className="mt-3 border-t border-line pt-3 text-xs text-ink-subtle">
            {product.page !== null && <p>Flyer page {product.page}</p>}
            {product.discountPercent !== null && (
              <p>{product.discountPercent}% discount</p>
            )}
            {product.lidlPlus && <p>Lidl Plus price</p>}
            {product.referencePrice !== null && (
              <p>
                Reference price:{" "}
                {product.currency === "EUR"
                  ? formatPrice(product.referencePrice)
                  : `${product.referencePrice.toFixed(2)} ${product.currency}`}
              </p>
            )}
            {product.unitPrices.map((unitPrice, index) => (
              <p key={`${unitPrice.raw}-${index}`}>{unitPrice.raw}</p>
            ))}
            {product.warnings.length > 0 && (
              <p className="mt-1 text-ink-muted">
                Extraction warnings: {product.warnings.join(", ")}
              </p>
            )}
          </div>
        ) : (
          <p className="mt-3 border-t border-line pt-3 text-xs text-ink-subtle">
            Last seen{" "}
            <span aria-hidden="true" className="px-0.5">
              ·
            </span>
            <time dateTime={product.lastSeen} className="font-medium text-ink-muted">
              {formatLastSeen(product.lastSeen)}
            </time>
          </p>
        )}
      </div>
    </article>
  );
}
