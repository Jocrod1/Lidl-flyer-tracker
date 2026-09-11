import { FilterBar } from "@/components/filters/FilterBar";
import { ProductGrid } from "@/components/products/ProductGrid";
import { SearchHero } from "@/components/search/SearchHero";
import { Container } from "@/components/ui/Container";
import type { Product } from "@/lib/products";

export interface ProductExplorerProps {
  products: Product[];
  categories: readonly string[];
  brands: readonly string[];
  latestFlyerLabel: string;
}

/**
 * Screen composition for the product explorer.
 *
 * Receives an already-resolved product list, so the page above it owns data
 * access and this stays a pure presentation layer.
 */
export function ProductExplorer({
  products,
  categories,
  brands,
  latestFlyerLabel,
}: ProductExplorerProps) {
  return (
    <>
      <SearchHero
        productCount={products.length}
        categoryCount={categories.length}
        latestFlyerLabel={latestFlyerLabel}
      />

      <Container className="py-8 sm:py-10">
        <FilterBar
          categories={categories}
          brands={brands}
          resultCount={products.length}
        />

        <div className="mt-8 flex items-baseline justify-between gap-4">
          <h2 className="text-lg font-bold tracking-tight text-ink sm:text-xl">
            All products
          </h2>
          <p className="shrink-0 text-sm text-ink-muted">Most recent first</p>
        </div>

        <div className="mt-4 sm:mt-5">
          <ProductGrid products={products} />
        </div>
      </Container>
    </>
  );
}
