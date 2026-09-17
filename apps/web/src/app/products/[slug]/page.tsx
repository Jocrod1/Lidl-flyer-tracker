import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ProductDetail } from "@/components/products/ProductDetail";
import { getProductDetail, getProductSlugs } from "@/lib/products";

/** Prebuild every known product slug; unknown slugs fall through to `notFound()`. */
export function generateStaticParams() {
  return getProductSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const product = getProductDetail(slug);

  if (!product) {
    return { title: "Product not found" };
  }

  return {
    title: product.name,
    description: `${product.brand} ${product.name} — price history and flyer appearances tracked by Lidl Tracker.`,
  };
}

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const product = getProductDetail(slug);

  if (!product) {
    notFound();
  }

  return <ProductDetail product={product} />;
}
