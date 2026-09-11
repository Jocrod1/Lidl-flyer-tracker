import Link from "next/link";

import { Container } from "@/components/ui/Container";

export default function NotFound() {
  return (
    <Container className="py-20 sm:py-28">
      <div className="mx-auto max-w-md text-center">
        <p className="text-[0.6875rem] font-bold uppercase tracking-[0.12em] text-ink-subtle">
          404
        </p>
        <h1 className="mt-3 text-2xl font-bold tracking-tight text-ink sm:text-3xl">
          Not tracked yet
        </h1>
        <p className="mt-3 text-base leading-7 text-ink-muted">
          This page doesn&apos;t exist yet. Product detail and flyer views are
          still being built.
        </p>
        <Link
          href="/"
          className="mt-7 inline-flex h-11 items-center rounded-xl bg-brand px-5 text-sm font-semibold text-white transition-colors hover:bg-brand-strong"
        >
          Back to products
        </Link>
      </div>
    </Container>
  );
}
