import { cn } from "@/lib/cn";

/**
 * Page-level horizontal gutter and max width.
 *
 * Caps out at ~1280px so the product grid stays readable on wide displays
 * instead of stretching edge to edge.
 */
export function Container({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8", className)}>
      {children}
    </div>
  );
}
