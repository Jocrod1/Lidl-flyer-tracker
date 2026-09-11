import type { PackagingShape } from "@/lib/products";
import { cn } from "@/lib/cn";

/**
 * Generated packaging artwork.
 *
 * The ingestion pipeline does not capture product photography yet, so each
 * product is drawn from its declared packaging shape and tint. This keeps the
 * grid visually varied without scraping Lidl or pulling in a remote image
 * dependency. When `Product.imageUrl` starts arriving, this component is the
 * single place that needs to learn about `next/image`.
 */

const LABEL = (
  <>
    <rect x="74" y="106" width="52" height="30" rx="4" fill="#ffffff" opacity="0.92" />
    <rect x="82" y="114" width="36" height="4" rx="2" fill="currentColor" opacity="0.35" />
    <rect x="82" y="123" width="24" height="4" rx="2" fill="currentColor" opacity="0.2" />
  </>
);

const SHAPES: Record<PackagingShape, React.ReactNode> = {
  bottle: (
    <>
      <path
        d="M88 26h24v22c0 6 22 14 22 34v80a14 14 0 0 1-14 14H80a14 14 0 0 1-14-14V82c0-20 22-28 22-34V26Z"
        fill="currentColor"
      />
      <rect x="86" y="20" width="28" height="12" rx="4" fill="currentColor" opacity="0.55" />
      {LABEL}
    </>
  ),
  carton: (
    <>
      <path d="M58 48h84v122a6 6 0 0 1-6 6H64a6 6 0 0 1-6-6V48Z" fill="currentColor" />
      <path d="M58 48 74 26h52l16 22H58Z" fill="currentColor" opacity="0.55" />
      <path d="M74 26h52v8H74z" fill="currentColor" opacity="0.75" />
      {LABEL}
    </>
  ),
  block: (
    <>
      <rect x="48" y="58" width="104" height="90" rx="12" fill="currentColor" />
      <rect x="48" y="58" width="104" height="18" rx="9" fill="currentColor" opacity="0.5" />
      <rect x="70" y="92" width="60" height="34" rx="5" fill="#ffffff" opacity="0.92" />
      <rect x="80" y="101" width="40" height="4" rx="2" fill="currentColor" opacity="0.35" />
      <rect x="80" y="110" width="26" height="4" rx="2" fill="currentColor" opacity="0.2" />
    </>
  ),
  jar: (
    <>
      <rect x="72" y="30" width="56" height="18" rx="6" fill="currentColor" opacity="0.6" />
      <path d="M66 62a16 16 0 0 1 16-16h36a16 16 0 0 1 16 16v98a14 14 0 0 1-14 14H80a14 14 0 0 1-14-14V62Z" fill="currentColor" />
      {LABEL}
    </>
  ),
  box: (
    <>
      <rect x="58" y="34" width="84" height="142" rx="7" fill="currentColor" />
      <rect x="58" y="34" width="84" height="20" rx="7" fill="currentColor" opacity="0.5" />
      {LABEL}
    </>
  ),
  bag: (
    <>
      <path d="M58 62q42-20 84 0v96q-42 20-84 0V62Z" fill="currentColor" />
      <path d="M58 62q42-20 84 0-42 14-84 0Z" fill="currentColor" opacity="0.5" />
      {LABEL}
    </>
  ),
  tray: (
    <>
      <rect x="40" y="66" width="120" height="84" rx="14" fill="currentColor" />
      <rect x="52" y="76" width="96" height="64" rx="10" fill="#ffffff" opacity="0.22" />
      <rect x="66" y="96" width="68" height="28" rx="5" fill="#ffffff" opacity="0.92" />
      <rect x="76" y="104" width="44" height="4" rx="2" fill="currentColor" opacity="0.35" />
      <rect x="76" y="113" width="28" height="4" rx="2" fill="currentColor" opacity="0.2" />
    </>
  ),
  can: (
    <>
      <rect x="70" y="38" width="60" height="140" rx="12" fill="currentColor" />
      <ellipse cx="100" cy="42" rx="30" ry="9" fill="currentColor" opacity="0.55" />
      {LABEL}
    </>
  ),
  loaf: (
    <>
      <path d="M44 156c0-58 20-92 56-92s56 34 56 92H44Z" fill="currentColor" />
      <path d="M70 92q30-16 60 0" stroke="#ffffff" strokeOpacity="0.3" strokeWidth="6" strokeLinecap="round" fill="none" />
      <path d="M64 116q36-16 72 0" stroke="#ffffff" strokeOpacity="0.25" strokeWidth="6" strokeLinecap="round" fill="none" />
    </>
  ),
  tub: (
    <>
      <path d="M62 62h76l-10 108a8 8 0 0 1-8 7H80a8 8 0 0 1-8-7L62 62Z" fill="currentColor" />
      <rect x="56" y="48" width="88" height="18" rx="7" fill="currentColor" opacity="0.55" />
      {LABEL}
    </>
  ),
};

export function ProductImage({
  shape,
  tint,
  className,
}: {
  shape: PackagingShape;
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
        preserveAspectRatio="xMidYMid meet"
        className="h-full w-full"
      >
        <ellipse cx="100" cy="176" rx="58" ry="9" fill="#10151c" opacity="0.07" />
        <g style={{ color: tint }}>{SHAPES[shape]}</g>
      </svg>
    </div>
  );
}
