import { SelectField } from "@/components/ui/SelectField";

const PRICE_RANGES = [
  "Any price",
  "Under 1 €",
  "1 € – 3 €",
  "3 € – 5 €",
  "Over 5 €",
] as const;

const LAST_SEEN_RANGES = [
  "Any time",
  "Last 7 days",
  "Last 30 days",
  "Last 3 months",
  "This year",
] as const;

export interface FilterBarProps {
  categories: readonly string[];
  brands: readonly string[];
  /** Number of products currently shown, rendered next to the controls. */
  resultCount: number;
}

/**
 * Filter controls for the product explorer.
 *
 * Presentational for now — the controls are uncontrolled and submitting does
 * nothing until the query layer exists.
 */
export function FilterBar({ categories, brands, resultCount }: FilterBarProps) {
  return (
    <form
      aria-label="Filter products"
      className="rounded-2xl border border-line bg-surface p-4 shadow-xs sm:p-5"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-ink">Filters</h2>
        <button
          type="reset"
          className="rounded-md px-1 text-sm font-medium text-brand transition-colors hover:text-brand-strong"
        >
          Reset
        </button>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <SelectField
          id="category"
          label="Category"
          options={["All categories", ...categories]}
        />
        <SelectField id="brand" label="Brand" options={["All brands", ...brands]} />
        <SelectField id="price" label="Price" options={PRICE_RANGES} />
        <SelectField id="last-seen" label="Last seen" options={LAST_SEEN_RANGES} />
      </div>

      <p className="mt-4 border-t border-line pt-3 text-sm text-ink-muted">
        <strong className="font-semibold text-ink">{resultCount}</strong>{" "}
        {resultCount === 1 ? "product" : "products"}
      </p>
    </form>
  );
}
