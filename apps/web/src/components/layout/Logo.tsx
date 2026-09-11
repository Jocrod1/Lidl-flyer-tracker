import Link from "next/link";

import { cn } from "@/lib/cn";

/**
 * Wordmark: a blue tile with a yellow dot, plus the product name.
 * Deliberately not a reproduction of the Lidl logo.
 */
export function Logo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn("group flex items-center gap-2.5 rounded-lg", className)}
    >
      <span
        aria-hidden="true"
        className="relative grid h-9 w-9 shrink-0 place-items-center rounded-[0.625rem] bg-brand shadow-sm"
      >
        <span className="h-3.5 w-3.5 rounded-full bg-highlight" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="text-[1.0625rem] font-bold tracking-tight text-ink">
          Lidl Tracker
        </span>
        <span className="mt-0.5 hidden text-[0.6875rem] font-medium uppercase tracking-[0.12em] text-ink-subtle sm:block">
          Flyer archive
        </span>
      </span>
    </Link>
  );
}
