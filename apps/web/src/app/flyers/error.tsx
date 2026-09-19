"use client"; // Error boundaries must be Client Components.

import { useEffect } from "react";

import { Container } from "@/components/ui/Container";

/**
 * Catches failures thrown by `/flyers` and `/flyers/[slug]` — most likely
 * the Flyer API being unreachable/misconfigured (`FlyerApiError`,
 * `MissingApiBaseUrlError` from `@/lib/flyers`). Deliberately generic and
 * user-facing: no stack traces, no raw error messages.
 *
 * Note: this Next.js version renamed the recovery callback from `reset`
 * to `retry` — see node_modules/next/dist/docs/.../10-error-handling.md.
 */
export default function FlyersError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Container className="py-16 text-center">
      <h1 className="text-2xl font-bold tracking-tight text-ink">
        We couldn&apos;t load flyer data
      </h1>
      <p className="mt-2 text-sm text-ink-muted">
        The Flyer API might be unavailable right now. Please try again in a
        moment.
      </p>
      <button
        type="button"
        onClick={retry}
        className="mt-6 inline-flex h-11 items-center justify-center rounded-lg bg-brand px-5 text-sm font-semibold text-white transition-colors hover:bg-brand-strong"
      >
        Try again
      </button>
    </Container>
  );
}
