import Link from "next/link";

import { cn } from "@/lib/cn";

export interface YearFilterProps {
  years: number[];
  /** `"all"` shows every archived flyer, regardless of year. */
  activeYear: number | "all";
}

/**
 * Lightweight year navigation for the archive.
 *
 * Plain links with a `year` query param rather than a client-side filter —
 * keeps the page a server component and the URL shareable/bookmarkable, and
 * leaves room to grow into real pagination once the archive spans more years.
 */
export function YearFilter({ years, activeYear }: YearFilterProps) {
  const pill = (href: string, label: string, active: boolean) => (
    <Link
      key={label}
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "inline-flex h-9 items-center justify-center rounded-lg px-4 text-sm font-semibold transition-colors",
        active
          ? "bg-surface text-brand shadow-xs"
          : "text-ink-muted hover:text-ink",
      )}
    >
      {label}
    </Link>
  );

  return (
    <nav aria-label="Filter by year" className="flex flex-wrap items-center gap-1 rounded-xl bg-surface-sunken p-1">
      {pill("/flyers", "All years", activeYear === "all")}
      {years.map((year) =>
        pill(`/flyers?year=${year}`, String(year), activeYear === year),
      )}
    </nav>
  );
}
