import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { FlyerProductCard } from "@/lib/products";

import { FlyerDetail } from "../FlyerDetail";

const flyer = {
  id: "1",
  slug: "flyer-1",
  title: "Flyer One",
  dateFrom: "2026-08-17",
  dateTo: "2026-08-23",
  productCount: 1,
  coverImage: "#0050aa",
};

function flyerCard(overrides: Partial<FlyerProductCard> = {}): FlyerProductCard {
  return {
    id: "card-1",
    cardIndex: 0,
    page: null,
    brand: null,
    name: null,
    description: null,
    quantity: null,
    price: null,
    referencePrice: null,
    unitPrices: [],
    discountPercent: null,
    lidlPlus: false,
    currency: "EUR",
    status: "partial",
    parserVersion: "0.1.0",
    warnings: [],
    notes: [],
    ...overrides,
  };
}

describe("FlyerDetail product section", () => {
  it("renders a specific empty state when the flyer has no extracted cards", () => {
    const markup = renderToStaticMarkup(
      <FlyerDetail flyer={flyer} products={[]} productsError={false} />,
    );

    expect(markup).toContain("No product cards in this flyer");
    expect(markup).not.toContain("Coming soon");
  });

  it("renders an API-error state while keeping the flyer detail available", () => {
    const markup = renderToStaticMarkup(
      <FlyerDetail flyer={flyer} products={[]} productsError />,
    );

    expect(markup).toContain("We couldn&#x27;t load this flyer&#x27;s product cards");
    expect(markup).toContain("Flyer One");
    expect(markup).toContain('href="/flyers"');
  });

  it("shows partial status and honest missing-field labels without a product link", () => {
    const markup = renderToStaticMarkup(
      <FlyerDetail
        flyer={flyer}
        products={[flyerCard({ status: "partial" })]}
        productsError={false}
      />,
    );

    expect(markup).toContain(">partial</span>");
    expect(markup).toContain("Name unavailable");
    expect(markup).toContain("Price unavailable");
    expect(markup).not.toContain('href="/products/');
  });
});
