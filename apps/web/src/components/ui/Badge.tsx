import { cn } from "@/lib/cn";

type Tone = "neutral" | "brand";

/** Small, non-interactive label used for categories and metadata. */
export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.06em]",
        tone === "brand"
          ? "bg-brand-soft text-brand-strong"
          : "bg-surface-sunken text-ink-muted",
        className,
      )}
    >
      {children}
    </span>
  );
}
