import { cn } from "@/lib/cn";

/**
 * Primary search affordance.
 *
 * Renders as a plain GET form so it degrades gracefully and can be wired to a
 * real `/?q=` query later without changing the markup.
 */
export function SearchBar({
  defaultValue,
  className,
}: {
  defaultValue?: string;
  className?: string;
}) {
  return (
    <form role="search" className={cn("w-full", className)}>
      <label htmlFor="q" className="sr-only">
        Search products
      </label>

      <div className="group relative flex items-center rounded-2xl border border-line bg-surface shadow-sm transition-shadow focus-within:border-brand focus-within:shadow-md">
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="pointer-events-none absolute left-4 h-5 w-5 text-ink-subtle"
        >
          <circle
            cx="11"
            cy="11"
            r="6.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.9"
          />
          <path
            d="M16 16l4.5 4.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.9"
            strokeLinecap="round"
          />
        </svg>

        <input
          id="q"
          name="q"
          type="search"
          autoComplete="off"
          defaultValue={defaultValue}
          placeholder="Search a product, brand or category…"
          className="h-14 w-full rounded-2xl bg-transparent pl-12 pr-4 text-base text-ink placeholder:text-ink-subtle focus:outline-none sm:h-16 sm:pr-36"
        />

        <button
          type="submit"
          className="absolute right-2 hidden h-12 items-center rounded-xl bg-brand px-5 text-sm font-semibold text-white transition-colors hover:bg-brand-strong sm:inline-flex"
        >
          Search
        </button>
      </div>
    </form>
  );
}
