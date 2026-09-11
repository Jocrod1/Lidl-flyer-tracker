"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const LINKS = [
  { href: "/", label: "Products" },
  { href: "/flyers", label: "Flyers" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/" || pathname.startsWith("/products");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Primary navigation.
 *
 * Only two destinations, so a hamburger would add friction for no gain: the
 * links stay visible and become full-width tap targets on small screens.
 */
export function MainNav({ className }: { className?: string }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Main" className={className}>
      <ul className="flex items-center gap-1 rounded-xl bg-surface-sunken p-1">
        {LINKS.map((link) => {
          const active = isActive(pathname, link.href);
          return (
            <li key={link.href} className="flex-1 sm:flex-none">
              <Link
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-9 items-center justify-center rounded-lg px-4 text-sm font-semibold transition-colors",
                  active
                    ? "bg-surface text-brand shadow-xs"
                    : "text-ink-muted hover:text-ink",
                )}
              >
                {link.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
