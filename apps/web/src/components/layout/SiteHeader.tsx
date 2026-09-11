import { Container } from "@/components/ui/Container";

import { Logo } from "./Logo";
import { MainNav } from "./MainNav";

export function SiteHeader() {
  return (
    // Sticky from `sm` up only: on phones the two-row header would otherwise
    // pin ~115px of chrome to the top of a short viewport.
    <header className="z-40 border-b border-line bg-surface/90 backdrop-blur sm:sticky sm:top-0 supports-[backdrop-filter]:bg-surface/75">
      <Container>
        <div className="flex h-16 items-center justify-between gap-4">
          <Logo />

          <div className="flex items-center gap-3">
            <MainNav className="hidden sm:block" />
            <span className="hidden items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-ink-muted md:inline-flex">
              <span
                aria-hidden="true"
                className="h-1.5 w-1.5 rounded-full bg-highlight"
              />
              Spain
            </span>
          </div>
        </div>

        {/* Small screens: navigation gets its own full-width row of tap targets. */}
        <div className="pb-3 sm:hidden">
          <MainNav />
        </div>
      </Container>
    </header>
  );
}
