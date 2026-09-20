import { describe, expect, it } from "vitest";

import type { FlyerSummaryDTO } from "../api";
import { mapFlyerSummary } from "../mapper";

function dto(overrides: Partial<FlyerSummaryDTO> = {}): FlyerSummaryDTO {
  return {
    id: 1,
    slug: "alimentacion-2026-08-17-a07bd0de",
    name: "Folleto Semanal",
    category: "ALIMENTACION",
    start_date: "2026-08-17",
    end_date: "2026-08-23",
    status: "STORED",
    product_count: 42,
    ...overrides,
  };
}

describe("mapFlyerSummary", () => {
  it("maps snake_case DTO fields onto FlyerArchiveItem", () => {
    const result = mapFlyerSummary(dto());

    expect(result).toEqual({
      id: "1",
      slug: "alimentacion-2026-08-17-a07bd0de",
      title: "Folleto Semanal",
      dateFrom: "2026-08-17",
      dateTo: "2026-08-23",
      productCount: 42,
      coverImage: expect.stringMatching(/^#[0-9a-f]{6}$/i),
      isCurrent: undefined,
    });
  });

  it("falls back to category, then a generic label, when name is blank", () => {
    expect(mapFlyerSummary(dto({ name: "" })).title).toBe("ALIMENTACION");
    expect(mapFlyerSummary(dto({ name: "", category: "" })).title).toBe("Flyer #1");
  });

  it("maps null start_date/end_date to empty strings rather than the string 'null'", () => {
    const result = mapFlyerSummary(dto({ start_date: null, end_date: null }));

    expect(result.dateFrom).toBe("");
    expect(result.dateTo).toBe("");
  });

  it("sets isCurrent only when explicitly requested", () => {
    expect(mapFlyerSummary(dto()).isCurrent).toBeUndefined();
    expect(mapFlyerSummary(dto(), { isCurrent: true }).isCurrent).toBe(true);
  });

  it("produces a deterministic, stable tint per flyer id", () => {
    const a = mapFlyerSummary(dto({ id: 7 }));
    const b = mapFlyerSummary(dto({ id: 7 }));

    expect(a.coverImage).toBe(b.coverImage);
  });
});
