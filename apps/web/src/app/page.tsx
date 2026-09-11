export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center bg-zinc-50 dark:bg-black">
      <main className="flex w-full max-w-md flex-1 flex-col items-center gap-8 px-6 py-16 sm:max-w-lg">
        <div className="flex flex-col items-center gap-2 text-center">
          <span className="h-1 w-10 rounded-full bg-accent" aria-hidden />
          <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
            Lidl Tracker
          </h1>
          <p className="max-w-xs text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            Search products from recent Lidl Spain flyers and see how they
            change over time.
          </p>
        </div>

        <label htmlFor="product-search" className="sr-only">
          Search products
        </label>
        <input
          id="product-search"
          type="search"
          disabled
          placeholder="Search for a product (coming soon)"
          className="w-full rounded-full border border-black/10 bg-white px-5 py-3 text-sm text-zinc-900 placeholder:text-zinc-400 shadow-sm outline-none disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-100"
        />

        <p className="text-center text-xs text-zinc-400 dark:text-zinc-600">
          Foundation scaffold — product search and flyer data are not wired up
          yet.
        </p>
      </main>
    </div>
  );
}
