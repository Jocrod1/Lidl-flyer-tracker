import { Container } from "@/components/ui/Container";

/**
 * Streamed while `/flyers` and `/flyers/[slug]` fetch from the Flyer API
 * (both pages are dynamically rendered — see the comment in
 * `app/flyers/[slug]/page.tsx`). Next wraps the page in a Suspense
 * boundary using this file automatically; no changes needed per route.
 */
export default function FlyersLoading() {
  return (
    <Container className="py-16 text-center">
      <p className="text-sm font-medium text-ink-muted">Loading flyers…</p>
    </Container>
  );
}
