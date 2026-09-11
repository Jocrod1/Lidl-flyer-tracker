import { ProductExplorer } from "@/components/products/ProductExplorer";
import {
  formatLastSeen,
  getBrands,
  getCategories,
  getProducts,
} from "@/lib/products";

export default function Home() {
  // Data access lives here so it can be swapped for an API call without
  // touching any of the presentation components below.
  const products = getProducts();
  const categories = getCategories();
  const brands = getBrands();

  const flyerDates = products.map((product) => product.lastSeen).sort();
  const latestFlyer = flyerDates.at(-1);

  return (
    <ProductExplorer
      products={products}
      categories={categories}
      brands={brands}
      latestFlyerLabel={latestFlyer ? formatLastSeen(latestFlyer) : "—"}
    />
  );
}
