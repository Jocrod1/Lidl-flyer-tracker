import path from "node:path";

import { defineConfig } from "vitest/config";

/**
 * Minimal vitest config — only wires up the `@/*` path alias already used
 * throughout `src/` (see tsconfig.json) so tests can import the same way
 * application code does. No React/DOM environment is configured because
 * the current tests only exercise plain TypeScript modules
 * (`lib/flyers/*`), not components.
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
