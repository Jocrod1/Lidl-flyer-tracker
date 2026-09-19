import { afterEach, describe, expect, it, vi } from "vitest";

import { FlyerNotFoundError, type FlyerSummaryDTO } from "../api";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    fetchFlyerList: vi.fn(),
    fetchFlyerBySlug: vi.fn(),
  };
});

const { fetchFlyerBySlug, fetchFlyerList } = await import("../api");
const { FlyerArchiveEmptyError, getFlyerArchive, getFlyerDetail } = await import("../api-flyers");

const mockedFetchFlyerList = vi.mocked(fetchFlyerList);
const mockedFetchFlyerBySlug = vi.mocked(fetchFlyerBySlug);

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

afterEach(() => {
  vi.clearAllMocks();
});

describe("getFlyerArchive", () => {
  it("throws FlyerArchiveEmptyError when the API returns no flyers", async () => {
    mockedFetchFlyerList.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 });

    await expect(getFlyerArchive()).rejects.toThrow(FlyerArchiveEmptyError);
  });

  it("treats the first item as current and excludes it from pastFlyers", async () => {
    mockedFetchFlyerList.mockResolvedValue({
      items: [dto({ id: 2, start_date: "2026-08-24" }), dto({ id: 1 })],
      total: 2,
      page: 1,
      page_size: 100,
    });

    const archive = await getFlyerArchive();

    expect(archive.currentFlyer.id).toBe("2");
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
