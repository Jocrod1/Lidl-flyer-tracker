import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { FlyerDetail } from "@/components/flyers/FlyerDetail";
import { formatDateRange, getFlyer, getFlyerSlugs } from "@/lib/flyers";

/** Prebuild every known flyer slug; unknown slugs fall through to `notFound()`. */
export function generateStaticParams() {
  return getFlyerSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const flyer = getFlyer(slug);

  if (!flyer) {
    return { title: "Flyer not found" };
  }

  return {
    title: flyer.title,
    description: `${flyer.title} (${formatDateRange(flyer.dateFrom, flyer.dateTo)}) — browse this Lidl Spain flyer on Lidl Tracker.`,
  };
}

export default async function FlyerDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const flyer = getFlyer(slug);

  if (!flyer) {
    notFound();
  }

  return <FlyerDetail flyer={flyer} />;
}
