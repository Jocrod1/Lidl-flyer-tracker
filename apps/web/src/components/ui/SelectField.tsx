import { cn } from "@/lib/cn";

export interface SelectFieldProps {
  id: string;
  label: string;
  /** First entry acts as the "no filter applied" option. */
  options: readonly string[];
  defaultValue?: string;
  className?: string;
}

/**
 * Native select wrapped in a labelled field.
 *
 * Native controls give us free mobile pickers and accessibility; the filters are
 * presentational for now, so the select stays uncontrolled.
 */
export function SelectField({
  id,
  label,
  options,
  defaultValue,
  className,
}: SelectFieldProps) {
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <label
        htmlFor={id}
        className="text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-ink-subtle"
      >
        {label}
      </label>
      <div className="relative">
        <select
          id={id}
          name={id}
          defaultValue={defaultValue ?? options[0]}
          className="h-11 w-full cursor-pointer appearance-none truncate rounded-lg border border-line bg-surface pl-3 pr-9 text-sm font-medium text-ink shadow-xs transition-colors hover:border-line-strong focus:border-brand focus:outline-none"
        >
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle"
        >
          <path
            d="M6 8l4 4 4-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </div>
  );
}
