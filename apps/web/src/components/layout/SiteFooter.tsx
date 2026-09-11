import { Container } from "@/components/ui/Container";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-line bg-surface">
      <Container>
        <div className="flex flex-col gap-2 py-8 text-xs leading-5 text-ink-subtle sm:flex-row sm:items-center sm:justify-between">
          <p>
            Lidl Tracker — an independent archive of Lidl Spain weekly flyer
            products.
          </p>
          <p>Not affiliated with or endorsed by Lidl.</p>
        </div>
      </Container>
    </footer>
  );
}
