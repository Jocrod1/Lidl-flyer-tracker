export function ArchiveHeader({ flyerCount }: { flyerCount: number }) {
  return (
    <div className="max-w-2xl">
      <h1 className="text-pretty text-3xl font-bold leading-tight tracking-tight text-ink sm:text-4xl">
        Flyer Archive
      </h1>
      <p className="mt-3 text-pretty text-base leading-7 text-ink-muted">
        Browse previous Lidl Spain flyers and quickly find what was available
        in a particular week.
      </p>
      <p className="mt-2 text-sm text-ink-subtle">
        <strong className="font-semibold text-ink-muted">{flyerCount}</strong>{" "}
        flyers archived
      </p>
    </div>
  );
}
