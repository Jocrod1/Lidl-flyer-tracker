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

export interface FlyerProductQuantityDTO {
  value: number | null;
  unit: string | null;
  count: number | null;
  total: number | null;
  approximate: boolean;
  values: number[];
  raw: string;
}

export interface FlyerProductUnitPriceDTO {
  value: number;
  unit: string;
  basis: number;
  per_unit: number;
  raw: string;
}

/** Raw response shape for one flyer-specific extracted card observation. */
export interface FlyerProductCardDTO {
  id: string;
  card_index: number;
  page: number | null;
  brand: string | null;
  name: string | null;
  description: string | null;
  quantity: FlyerProductQuantityDTO | null;
  price: number | null;
  reference_price: number | null;
  unit_prices: FlyerProductUnitPriceDTO[];
  discount_percent: number | null;
  lidl_plus: boolean;
  currency: string;
  status: "ok" | "partial" | "failed";
  parser_version: string;
  warnings: string[];
  notes: string[];
}

/** Raw response shape for `GET /v1/flyers/{slug}/products`. */
export interface FlyerProductsResponseDTO {
  items: FlyerProductCardDTO[];
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

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isFlyerProductQuantityDTO(value: unknown): value is FlyerProductQuantityDTO {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const quantity = value as Record<string, unknown>;
  return (
    isNullableNumber(quantity.value) &&
    (typeof quantity.unit === "string" || quantity.unit === null) &&
    (quantity.count === null ||
      (typeof quantity.count === "number" && Number.isInteger(quantity.count))) &&
    isNullableNumber(quantity.total) &&
    typeof quantity.approximate === "boolean" &&
    Array.isArray(quantity.values) &&
    quantity.values.every((item) => typeof item === "number" && Number.isFinite(item)) &&
    typeof quantity.raw === "string"
  );
}

function isFlyerProductUnitPriceDTO(value: unknown): value is FlyerProductUnitPriceDTO {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const unitPrice = value as Record<string, unknown>;
  return (
    typeof unitPrice.value === "number" &&
    Number.isFinite(unitPrice.value) &&
    typeof unitPrice.unit === "string" &&
    typeof unitPrice.basis === "number" &&
    Number.isInteger(unitPrice.basis) &&
    typeof unitPrice.per_unit === "number" &&
    Number.isFinite(unitPrice.per_unit) &&
    typeof unitPrice.raw === "string"
  );
}

function isFlyerProductCardDTO(value: unknown): value is FlyerProductCardDTO {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const card = value as Record<string, unknown>;
  return (
    typeof card.id === "string" &&
    typeof card.card_index === "number" &&
    Number.isInteger(card.card_index) &&
    (card.page === null || (typeof card.page === "number" && Number.isInteger(card.page))) &&
    (typeof card.brand === "string" || card.brand === null) &&
    (typeof card.name === "string" || card.name === null) &&
    (typeof card.description === "string" || card.description === null) &&
    (card.quantity === null || isFlyerProductQuantityDTO(card.quantity)) &&
    isNullableNumber(card.price) &&
    isNullableNumber(card.reference_price) &&
    Array.isArray(card.unit_prices) &&
    card.unit_prices.every(isFlyerProductUnitPriceDTO) &&
    (card.discount_percent === null ||
      (typeof card.discount_percent === "number" &&
        Number.isInteger(card.discount_percent))) &&
    typeof card.lidl_plus === "boolean" &&
    typeof card.currency === "string" &&
    (card.status === "ok" || card.status === "partial" || card.status === "failed") &&
    typeof card.parser_version === "string" &&
    Array.isArray(card.warnings) &&
    card.warnings.every((warning) => typeof warning === "string") &&
    Array.isArray(card.notes) &&
    card.notes.every((note) => typeof note === "string")
  );
}

function isFlyerProductsResponseDTO(value: unknown): value is FlyerProductsResponseDTO {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const page = value as Record<string, unknown>;
  return (
    Array.isArray(page.items) &&
    page.items.every(isFlyerProductCardDTO) &&
    typeof page.total === "number" &&
    Number.isInteger(page.total) &&
    typeof page.page === "number" &&
    Number.isInteger(page.page) &&
    typeof page.page_size === "number" &&
    Number.isInteger(page.page_size) &&
    page.total >= 0 &&
    page.page >= 1 &&
    page.page_size >= 1 &&
    page.items.length <= page.page_size
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

export interface FlyerProductsParams {
  page?: number;
  page_size?: number;
}

/** `GET /v1/flyers/{slug}/products` — one page of flyer-specific card observations. */
export async function fetchFlyerProducts(
  slug: string,
  params: FlyerProductsParams = {},
): Promise<FlyerProductsResponseDTO> {
  const search = new URLSearchParams();
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.page_size !== undefined) search.set("page_size", String(params.page_size));

  const query = search.toString();
  const path = `/v1/flyers/${encodeURIComponent(slug)}/products${query ? `?${query}` : ""}`;
  try {
    const response = await apiFetch(path);
    if (!isFlyerProductsResponseDTO(response)) {
      throw new FlyerApiError("Flyer API returned an invalid flyer products response.");
    }
    return response;
  } catch (error) {
    if (error instanceof FlyerApiError && error.status === 404) {
      throw new FlyerNotFoundError(slug);
    }
    throw error;
  }
}
