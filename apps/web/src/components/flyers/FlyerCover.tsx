import { cn } from "@/lib/cn";

/**
 * Generated flyer cover artwork.
 *
 * Mirrors `ProductImage`: no flyer scans or remote imagery exist yet, so each
 * cover is drawn from the flyer's declared tint. When a real cover/PDF preview
 * URL starts arriving from the backend, this stays the single place that
 * needs to learn about `next/image`.
 */
export function FlyerCover({
  tint,
  className,
}: {
  tint: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative flex items-center justify-center overflow-hidden bg-surface-muted",
        className,
      )}
    >
      <svg
        viewBox="0 0 200 200"
        role="presentation"
        aria-hidden="true"
        preserveAspectRatio="xMidYMid slice"
        className="h-full w-full"
      >
        <rect width="200" height="200" fill={tint} />
        <rect y="0" width="200" height="56" fill="#ffffff" opacity="0.14" />
        <circle cx="176" cy="24" r="34" fill="#ffffff" opacity="0.12" />
        <circle cx="18" cy="182" r="46" fill="#ffffff" opacity="0.1" />
        <rect x="24" y="88" width="96" height="16" rx="8" fill="#ffffff" opacity="0.92" />
        <rect x="24" y="112" width="60" height="10" rx="5" fill="#ffffff" opacity="0.6" />
      </svg>
    </div>
  );
}
