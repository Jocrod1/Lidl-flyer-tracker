import { ArchiveHeader } from "@/components/flyers/ArchiveHeader";
import { FeaturedFlyer } from "@/components/flyers/FeaturedFlyer";
import { FlyerGrid } from "@/components/flyers/FlyerGrid";
import { YearFilter } from "@/components/flyers/YearFilter";
import { Container } from "@/components/ui/Container";
import type { FlyerArchiveItem } from "@/lib/flyers";

export interface FlyerArchiveProps {
  currentFlyer: FlyerArchiveItem;
  pastFlyers: FlyerArchiveItem[];
  totalFlyerCount: number;
  years: number[];
  activeYear: number | "all";
}

/**
 * Screen composition for the Flyer Archive (`/flyers`).
 *
 * Receives already-resolved, already-filtered flyer data, so the page above
 * it owns data access (and query-param parsing) and this stays a pure
 * presentation layer, matching the Product Explorer's pattern.
 */
export function FlyerArchive({
  currentFlyer,
  pastFlyers,
  totalFlyerCount,
  years,
  activeYear,
}: FlyerArchiveProps) {
  return (
    <Container className="py-8 sm:py-10">
      <ArchiveHeader flyerCount={totalFlyerCount} />

      <div className="mt-8 sm:mt-10">
        <FeaturedFlyer flyer={currentFlyer} />
      </div>

      <div className="mt-10 sm:mt-14">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-lg font-bold tracking-tight text-ink sm:text-xl">
            Previous flyers
          </h2>
          <YearFilter years={years} activeYear={activeYear} />
        </div>

        <div className="mt-4 sm:mt-5">
          <FlyerGrid flyers={pastFlyers} />
        </div>
      </div>
    </Container>
  );
}
