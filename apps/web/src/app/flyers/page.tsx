import type { Metadata } from "next";

import { FlyerArchive } from "@/components/flyers/FlyerArchive";
import {
  getCurrentFlyer,
  getFlyerYears,
  getFlyers,
  getPastFlyers,
} from "@/lib/flyers";

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
  // touching any of the presentation components below.
  const { year } = await searchParams;
  const currentFlyer = getCurrentFlyer();
  const years = getFlyerYears();

  const requestedYear = year ? Number(year) : undefined;
  const activeYear =
    requestedYear && years.includes(requestedYear) ? requestedYear : "all";

  const pastFlyers = getPastFlyers().filter((flyer) =>
    activeYear === "all" ? true : flyer.dateFrom.startsWith(String(activeYear)),
  );

  return (
    <FlyerArchive
      currentFlyer={currentFlyer}
      pastFlyers={pastFlyers}
      totalFlyerCount={getFlyers().length}
      years={years}
      activeYear={activeYear}
    />
  );
}
