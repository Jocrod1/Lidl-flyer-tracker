import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { FlyerDetail } from "@/components/flyers/FlyerDetail";
import {
  FlyerApiError,
  FlyerNotFoundError,
  formatDateRange,
  getFlyerDetail,
  getFlyerProducts,
} from "@/lib/flyers";
import type { FlyerProductCard } from "@/lib/products";

// No generateStaticParams() here: flyers are ingested weekly and the API
// is now the source of truth, so prebuilding every slug at build time
// would mean redeploying the whole app for each new flyer. Pages render
// dynamically instead — `fetchFlyerBySlug` fetches with `cache: "no-store"`
// (see @/lib/flyers/api.ts), so every request gets current data. See
// docs/backend-frontend-integration-plan.md Phase 2 "Static generation vs
// dynamic rendering" for the full reasoning.

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;

  try {
    const flyer = await getFlyerDetail(slug);
    return {
      title: flyer.title,
      description: `${flyer.title} (${formatDateRange(flyer.dateFrom, flyer.dateTo)}) — browse this Lidl Spain flyer on Lidl Tracker.`,
    };
  } catch {
    // Metadata generation must never throw — an unknown slug or a
    // transient API error both fall back to a generic title here; the
    // page component below is what actually renders notFound()/error UI.
    return { title: "Flyer not found" };
  }
}

export default async function FlyerDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  let flyer;
  try {
    flyer = await getFlyerDetail(slug);
  } catch (error) {
    if (error instanceof FlyerNotFoundError) {
      notFound();
    }
    // Any other failure (network error, API down, etc.) bubbles up to
    // the nearest error boundary — see app/flyers/error.tsx.
    throw error;
  }

  let products: FlyerProductCard[] = [];
  let productsError = false;
  try {
    products = await getFlyerProducts(slug);
  } catch (error) {
    if (error instanceof FlyerNotFoundError) {
      notFound();
    }
    if (!(error instanceof FlyerApiError)) {
      throw error;
    }
    productsError = true;
  }

  return (
    <FlyerDetail
      flyer={flyer}
      products={products}
      productsError={productsError}
    />
  );
}
