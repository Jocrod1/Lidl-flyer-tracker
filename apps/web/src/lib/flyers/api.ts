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

async function apiFetch<T>(path: string): Promise<T> {
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

  return (await response.json()) as T;
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
  return apiFetch<FlyerListResponseDTO>(`/v1/flyers${query ? `?${query}` : ""}`);
}

/** `GET /v1/flyers/{slug}` — throws `FlyerNotFoundError` on a 404 response. */
export async function fetchFlyerBySlug(slug: string): Promise<FlyerSummaryDTO> {
  try {
    return await apiFetch<FlyerSummaryDTO>(`/v1/flyers/${encodeURIComponent(slug)}`);
  } catch (error) {
    if (error instanceof FlyerApiError && error.status === 404) {
      throw new FlyerNotFoundError(slug);
    }
    throw error;
  }
}
