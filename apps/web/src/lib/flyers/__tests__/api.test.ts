import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  FlyerApiError,
  FlyerNotFoundError,
  MissingApiBaseUrlError,
  fetchFlyerBySlug,
  fetchFlyerList,
} from "../api";

const ORIGINAL_BASE_URL = process.env.LIDL_API_BASE_URL;

function jsonResponse(body: unknown, init: { status?: number } = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  process.env.LIDL_API_BASE_URL = ORIGINAL_BASE_URL;
  vi.unstubAllGlobals();
});

describe("fetchFlyerList", () => {
  beforeEach(() => {
    process.env.LIDL_API_BASE_URL = "http://localhost:8000";
  });

  it("requests /v1/flyers with no query params by default", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ items: [], total: 0, page: 1, page_size: 20 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchFlyerList();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/v1/flyers",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("forwards page, page_size, and year as query params", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ items: [], total: 0, page: 2, page_size: 5 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchFlyerList({ year: 2026, page: 2, page_size: 5 });

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toBe("http://localhost:8000/v1/flyers?page=2&page_size=5&year=2026");
  });

  it("strips a trailing slash from the configured base URL", async () => {
    process.env.LIDL_API_BASE_URL = "http://localhost:8000/";
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], total: 0, page: 1, page_size: 20 }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchFlyerList();

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/v1/flyers", expect.anything());
  });

  it("returns the parsed response body on success", async () => {
    const body = { items: [{ id: 1 }], total: 1, page: 1, page_size: 20 };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body)));

    const result = await fetchFlyerList();

    expect(result).toEqual(body);
  });

  it("throws FlyerApiError on a non-2xx response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, { status: 500 })));

    await expect(fetchFlyerList()).rejects.toThrow(FlyerApiError);
  });

  it("throws FlyerApiError when the network request itself fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

    await expect(fetchFlyerList()).rejects.toThrow(FlyerApiError);
  });

  it("throws MissingApiBaseUrlError when LIDL_API_BASE_URL is unset", async () => {
    delete process.env.LIDL_API_BASE_URL;
    vi.stubGlobal("fetch", vi.fn());

    await expect(fetchFlyerList()).rejects.toThrow(MissingApiBaseUrlError);
  });
});

describe("fetchFlyerBySlug", () => {
  beforeEach(() => {
    process.env.LIDL_API_BASE_URL = "http://localhost:8000";
  });

  it("returns the flyer on success", async () => {
    const dto = {
      id: 1,
      slug: "a",
      name: "A",
      category: "",
      start_date: null,
      end_date: null,
      status: "STORED",
      product_count: 0,
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(dto)));

    const result = await fetchFlyerBySlug("a");

    expect(result).toEqual(dto);
  });

  it("throws FlyerNotFoundError on a 404 response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Flyer not found" }, { status: 404 })),
    );

    await expect(fetchFlyerBySlug("unknown")).rejects.toThrow(FlyerNotFoundError);
  });

  it("URL-encodes the slug in the request path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}, { status: 404 }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchFlyerBySlug("a b").catch(() => {});

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/v1/flyers/a%20b",
      expect.anything(),
    );
  });
});
