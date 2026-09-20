export * from "./types";
export * from "./format";
export * from "./api-flyers";

/**
 * Mock data (`./mock-flyers`) is intentionally NOT re-exported here.
 *
 * The barrel now exposes the real API-backed accessors (`getFlyerArchive`,
 * `getFlyerDetail`) so `/flyers` and `/flyers/[slug]` always talk to
 * `LIDL_API_BASE_URL` in every environment — a missing/unreachable API
 * surfaces as a visible error (see `app/flyers/error.tsx`), not a silent
 * fallback to fake data. For local development or tests that don't need a
 * running API, import the mock accessors directly:
 *
 *   import { getFlyers, getFlyer } from "@/lib/flyers/mock-flyers";
 */
