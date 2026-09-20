import { describe, expect, it } from "vitest";

import { formatDateRange } from "../format";

describe("formatDateRange", () => {
  it("renders a friendly fallback when either date is missing", () => {
    expect(formatDateRange("", "")).toBe("Dates unavailable");
    expect(formatDateRange("2026-08-17", "")).toBe("Dates unavailable");
    expect(formatDateRange("", "2026-08-23")).toBe("Dates unavailable");
  });

  it("formats a same-month range without repeating the month", () => {
    expect(formatDateRange("2026-09-07", "2026-09-13")).toBe("7 – 13 Sep 2026");
  });

  it("formats a cross-month range with both month labels", () => {
    expect(formatDateRange("2026-07-27", "2026-08-02")).toBe("27 Jul – 2 Aug 2026");
  });
});
