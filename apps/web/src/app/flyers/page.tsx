import type { Metadata } from "next";

import { FlyerArchive } from "@/components/flyers/FlyerArchive";
import { getFlyerArchive } from "@/lib/flyers";

export const metadata: Metadata = {
  title: "Flyer Archive",
  description:
    "Browse previous Lidl Spain flyers and quickly find what was available in a particular week.",
};

export default async function FlyersPage({
  searchParams,
}: {
  searchParams: Promise<{ year?: string }>;
}) {
  // Data access lives here so it can be swapped for an API call without
  // touching any of the presentation components below. It now calls the
  // real Flyer API (see @/lib/flyers/api-flyers.ts) instead of mock data.
  const { year } = await searchParams;
  const requestedYear = year ? Number(year) : undefined;

  const archive = await getFlyerArchive({
    year: requestedYear !== undefined && Number.isFinite(requestedYear) ? requestedYear : undefined,
  });

  return (
    <FlyerArchive
      currentFlyer={archive.currentFlyer}
      pastFlyers={archive.pastFlyers}
      totalFlyerCount={archive.totalFlyerCount}
      years={archive.years}
      activeYear={archive.activeYear}
    />
  );
}
