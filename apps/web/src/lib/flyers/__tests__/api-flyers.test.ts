import { afterEach, describe, expect, it, vi } from "vitest";

import {
  FlyerApiError,
  FlyerNotFoundError,
  type FlyerProductCardDTO,
  type FlyerSummaryDTO,
} from "../api";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    fetchFlyerList: vi.fn(),
    fetchFlyerBySlug: vi.fn(),
    fetchFlyerProducts: vi.fn(),
  };
});

const { fetchFlyerBySlug, fetchFlyerList, fetchFlyerProducts } = await import("../api");
const { getFlyerArchive, getFlyerDetail, getFlyerProducts } = await import("../api-flyers");

const mockedFetchFlyerList = vi.mocked(fetchFlyerList);
const mockedFetchFlyerBySlug = vi.mocked(fetchFlyerBySlug);
const mockedFetchFlyerProducts = vi.mocked(fetchFlyerProducts);

function dto(overrides: Partial<FlyerSummaryDTO> = {}): FlyerSummaryDTO {
  return {
    id: 1,
    slug: "flyer-1",
    name: "Flyer One",
    category: "ALIMENTACION",
    start_date: "2026-08-17",
    end_date: "2026-08-23",
    status: "STORED",
    product_count: 10,
    ...overrides,
  };
}

function productCard(overrides: Partial<FlyerProductCardDTO> = {}): FlyerProductCardDTO {
  return {
    id: "card-1",
    card_index: 0,
    page: 1,
    brand: null,
    name: "Guacamole",
    description: null,
    quantity: null,
    price: 3.75,
    reference_price: null,
    unit_prices: [],
    discount_percent: null,
    lidl_plus: false,
    currency: "EUR",
    status: "partial",
    parser_version: "0.1.0",
    warnings: ["missing_brand"],
    notes: [],
    ...overrides,
  };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("getFlyerArchive", () => {
  it("returns an empty archive when the API has no flyers", async () => {
    mockedFetchFlyerList.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 });

    await expect(getFlyerArchive()).resolves.toMatchObject({
      currentFlyer: null,
      pastFlyers: [],
      totalFlyerCount: 0,
      years: [],
      activeYear: "all",
    });
  });

  it("treats the first item as current and excludes it from pastFlyers", async () => {
    mockedFetchFlyerList.mockResolvedValue({
      items: [dto({ id: 2, start_date: "2026-08-24" }), dto({ id: 1 })],
      total: 2,
      page: 1,
      page_size: 100,
    });

    const archive = await getFlyerArchive();

    expect(archive.currentFlyer?.id).toBe("2");
    expect(archive.pastFlyers.map((flyer) => flyer.id)).toEqual(["1"]);
    expect(archive.totalFlyerCount).toBe(2);
    expect(archive.activeYear).toBe("all");
    expect(mockedFetchFlyerList).toHaveBeenCalledTimes(1);
  });

  it("computes distinct years across the full archive, newest first", async () => {
    mockedFetchFlyerList.mockResolvedValue({
      items: [
        dto({ id: 3, start_date: "2026-01-05" }),
        dto({ id: 2, start_date: "2025-08-24" }),
        dto({ id: 1, start_date: "2025-08-17" }),
      ],
      total: 3,
      page: 1,
      page_size: 100,
    });

    const archive = await getFlyerArchive();

    expect(archive.years).toEqual([2026, 2025]);
  });

  it("loads every API page before choosing the current flyer and year facets", async () => {
    const flyers = Array.from({ length: 205 }, (_, index) =>
      dto({
        id: 205 - index,
        slug: `flyer-${205 - index}`,
        start_date: index < 150 ? "2026-08-17" : "2025-08-17",
      }),
    );
    mockedFetchFlyerList.mockImplementation(async ({ page = 1 } = {}) => ({
      items: flyers.slice((page - 1) * 100, page * 100),
      total: flyers.length,
      page,
      page_size: 100,
    }));

    const archive = await getFlyerArchive();

    expect(mockedFetchFlyerList).toHaveBeenCalledTimes(3);
    expect(archive.currentFlyer?.id).toBe("205");
    expect(archive.pastFlyers).toHaveLength(204);
    expect(archive.years).toEqual([2026, 2025]);
  });

  it("makes a second request with ?year= only for a valid requested year", async () => {
    mockedFetchFlyerList.mockResolvedValueOnce({
      items: [dto({ id: 2, start_date: "2026-08-24" }), dto({ id: 1, start_date: "2025-08-17" })],
      total: 2,
      page: 1,
      page_size: 100,
    });
    mockedFetchFlyerList.mockResolvedValueOnce({
      items: [dto({ id: 1, start_date: "2025-08-17" })],
      total: 1,
      page: 1,
      page_size: 100,
    });

    const archive = await getFlyerArchive({ year: 2025 });

    expect(mockedFetchFlyerList).toHaveBeenCalledTimes(2);
    expect(mockedFetchFlyerList).toHaveBeenNthCalledWith(2, {
      page: 1,
      page_size: 100,
      year: 2025,
    });
    expect(archive.activeYear).toBe(2025);
    expect(archive.pastFlyers.map((flyer) => flyer.id)).toEqual(["1"]);
  });

  it("falls back to 'all' and skips the second request for an unknown year", async () => {
    mockedFetchFlyerList.mockResolvedValue({
      items: [dto({ id: 1, start_date: "2026-08-17" })],
      total: 1,
      page: 1,
      page_size: 100,
    });

    const archive = await getFlyerArchive({ year: 1999 });

    expect(archive.activeYear).toBe("all");
    expect(mockedFetchFlyerList).toHaveBeenCalledTimes(1);
  });
});

describe("getFlyerDetail", () => {
  it("maps the API response onto FlyerArchiveItem", async () => {
    mockedFetchFlyerBySlug.mockResolvedValue(dto());

    const flyer = await getFlyerDetail("flyer-1");

    expect(flyer.slug).toBe("flyer-1");
    expect(flyer.productCount).toBe(10);
  });

  it("propagates FlyerNotFoundError for an unknown slug", async () => {
    mockedFetchFlyerBySlug.mockRejectedValue(new FlyerNotFoundError("missing"));

    await expect(getFlyerDetail("missing")).rejects.toThrow(FlyerNotFoundError);
  });
});

describe("getFlyerProducts", () => {
  it("fetches every page and preserves flyer-specific partial card fields", async () => {
    const cards = Array.from({ length: 105 }, (_, index) =>
      productCard({
        id: `card-${index}`,
        card_index: index,
        status: index === 104 ? "failed" : "partial",
      }),
    );
    mockedFetchFlyerProducts.mockImplementation(async (_slug, { page = 1 } = {}) => ({
      items: cards.slice((page - 1) * 100, page * 100),
      total: cards.length,
      page,
      page_size: 100,
    }));

    const products = await getFlyerProducts("flyer-1");

    expect(mockedFetchFlyerProducts).toHaveBeenNthCalledWith(1, "flyer-1", {
      page: 1,
      page_size: 100,
    });
    expect(mockedFetchFlyerProducts).toHaveBeenNthCalledWith(2, "flyer-1", {
      page: 2,
      page_size: 100,
    });
    expect(products).toHaveLength(105);
    expect(products[0]).toMatchObject({
      id: "card-0",
      name: "Guacamole",
      brand: null,
      price: 3.75,
      status: "partial",
      warnings: ["missing_brand"],
    });
    expect(products[104].status).toBe("failed");
  });

  it("returns an empty array for a flyer with no cards", async () => {
    mockedFetchFlyerProducts.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    });

    await expect(getFlyerProducts("empty-flyer")).resolves.toEqual([]);
    expect(mockedFetchFlyerProducts).toHaveBeenCalledTimes(1);
  });

  it("propagates API errors instead of returning an empty result", async () => {
    mockedFetchFlyerProducts.mockRejectedValue(new FlyerApiError("API unavailable", 503));

    await expect(getFlyerProducts("flyer-1")).rejects.toThrow(FlyerApiError);
  });

  it("rejects inconsistent pagination metadata", async () => {
    mockedFetchFlyerProducts
      .mockResolvedValueOnce({
        items: Array.from({ length: 100 }, (_, index) =>
          productCard({ id: `card-${index}`, card_index: index }),
        ),
        total: 101,
        page: 1,
        page_size: 100,
      })
      .mockResolvedValueOnce({
        items: [productCard({ id: "card-101", card_index: 100 })],
        total: 102,
        page: 2,
        page_size: 100,
      });

    await expect(getFlyerProducts("flyer-1")).rejects.toThrow(
      "inconsistent flyer products pagination",
    );
  });
});
