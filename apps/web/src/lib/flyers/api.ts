/**
 * Server-side HTTP client for the Flyer API (`apps/api`, Phase 1).
 *
 * This module is imported only from Server Components / page-level data
 * access (`api-flyers.ts`) — never from Client Components — so it is safe
 * to read `process.env.LIDL_API_BASE_URL` directly and to assume it never
 * runs in the browser. Do not import this module from anything marked
 * `"use client"`.
 */

/** Raw response shape for a single flyer, exactly as FastAPI serializes it. */
export interface FlyerSummaryDTO {
  id: number;
  slug: string;
  name: string;
  category: string;
  start_date: string | null;
  end_date: string | null;
  status: string;
  product_count: number;
}

/** Raw response shape for `GET /v1/flyers`. */
export interface FlyerListResponseDTO {
  items: FlyerSummaryDTO[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Base error for anything that goes wrong talking to the Flyer API —
 * network failures, non-2xx responses, and missing configuration all
 * surface as this (or a subclass), never as a raw fetch/parse exception,
 * so callers can pattern-match on error type instead of HTTP mechanics.
 */
export class FlyerApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "FlyerApiError";
    this.status = status;
  }
}

/** Thrown when `GET /v1/flyers/{slug}` returns 404 — maps to Next's `notFound()`. */
export class FlyerNotFoundError extends FlyerApiError {
  constructor(slug: string) {
    super(`Flyer not found: ${slug}`, 404);
    this.name = "FlyerNotFoundError";
  }
}

/**
 * Thrown when `LIDL_API_BASE_URL` isn't configured.
 *
 * Deliberately loud rather than silently falling back to mock data — a
 * misconfigured production deployment should surface as a visible error
 * (caught by `app/flyers/error.tsx`), not as an app that quietly serves
 * fake flyers. For local development without the API, import accessors
 * from `@/lib/flyers/mock-flyers` directly instead.
 */
export class MissingApiBaseUrlError extends FlyerApiError {
  constructor() {
    super(
      "LIDL_API_BASE_URL is not set. Configure it to reach the Flyer API " +
        "(e.g. http://localhost:8000), or import mock accessors directly " +
        "from '@/lib/flyers/mock-flyers' for local development without a " +
        "running API.",
    );
    this.name = "MissingApiBaseUrlError";
  }
}

function getApiBaseUrl(): string {
  const baseUrl = process.env.LIDL_API_BASE_URL;
  if (!baseUrl) {
    throw new MissingApiBaseUrlError();
  }
  return baseUrl.replace(/\/+$/, "");
}

function isFlyerSummaryDTO(value: unknown): value is FlyerSummaryDTO {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const flyer = value as Record<string, unknown>;
  return (
    typeof flyer.id === "number" &&
    Number.isInteger(flyer.id) &&
    typeof flyer.slug === "string" &&
    typeof flyer.name === "string" &&
    typeof flyer.category === "string" &&
    (typeof flyer.start_date === "string" || flyer.start_date === null) &&
    (typeof flyer.end_date === "string" || flyer.end_date === null) &&
    typeof flyer.status === "string" &&
    typeof flyer.product_count === "number" &&
    Number.isInteger(flyer.product_count) &&
    flyer.product_count >= 0
  );
}

function isFlyerListResponseDTO(value: unknown): value is FlyerListResponseDTO {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const page = value as Record<string, unknown>;
  return (
    Array.isArray(page.items) &&
    page.items.every(isFlyerSummaryDTO) &&
    typeof page.total === "number" &&
    Number.isInteger(page.total) &&
    typeof page.page === "number" &&
    Number.isInteger(page.page) &&
    typeof page.page_size === "number" &&
    Number.isInteger(page.page_size) &&
    page.total >= 0 &&
    page.page >= 1 &&
    page.page_size >= 1
  );
}

async function apiFetch(path: string): Promise<unknown> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      headers: { Accept: "application/json" },
      // Correctness over caching for Phase 2: flyers are ingested weekly
      // and the archive is small, so there is no need for aggressive
      // caching yet, and skipping Next's Data Cache means failed/expired
      // responses are never accidentally served as "cached errors".
      // Revisit once traffic patterns justify `next: { revalidate }`.
      cache: "no-store",
    });
  } catch {
    throw new FlyerApiError(`Could not reach the Flyer API at ${url}`);
  }

  if (response.status === 404) {
    throw new FlyerApiError(`Not found: ${path}`, 404);
  }

  if (!response.ok) {
    throw new FlyerApiError(
      `Flyer API request failed (${response.status}): ${path}`,
      response.status,
    );
  }

  try {
    return await response.json();
  } catch {
    throw new FlyerApiError(`Flyer API returned invalid JSON: ${path}`);
  }
}

export interface FlyerListParams {
  page?: number;
  page_size?: number;
  year?: number;
}

/** `GET /v1/flyers` — thin wrapper, one-to-one with the API's query params. */
export async function fetchFlyerList(
  params: FlyerListParams = {},
): Promise<FlyerListResponseDTO> {
  const search = new URLSearchParams();
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.page_size !== undefined) search.set("page_size", String(params.page_size));
  if (params.year !== undefined) search.set("year", String(params.year));

  const query = search.toString();
  const response = await apiFetch(`/v1/flyers${query ? `?${query}` : ""}`);
  if (!isFlyerListResponseDTO(response)) {
    throw new FlyerApiError("Flyer API returned an invalid flyer list response.");
  }
  return response;
}

/** `GET /v1/flyers/{slug}` — throws `FlyerNotFoundError` on a 404 response. */
export async function fetchFlyerBySlug(slug: string): Promise<FlyerSummaryDTO> {
  try {
    const response = await apiFetch(`/v1/flyers/${encodeURIComponent(slug)}`);
    if (!isFlyerSummaryDTO(response)) {
      throw new FlyerApiError("Flyer API returned an invalid flyer response.");
    }
    return response;
  } catch (error) {
    if (error instanceof FlyerApiError && error.status === 404) {
      throw new FlyerNotFoundError(slug);
    }
    throw error;
  }
}
