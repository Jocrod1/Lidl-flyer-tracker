# Lidl Tracker: Backend ↔ Frontend Integration Plan

This document describes the current backend and frontend architecture and the minimum changes required to connect them. It is an implementation plan only; it does not implement the API, change the schema, or replace the frontend mocks.

## Decisions

- Introduce a small FastAPI service under `apps/api`.
- Keep the Next.js app focused on presentation and server-side API consumption.
- Initially derive products from `product_cards` grouped by normalized name and brand.
- Do not introduce a canonical `products` table or entity-resolution pipeline in the first integration.
- Keep the frontend mock accessors as a migration fallback while replacing their implementations feature by feature.

## 1. Current Architecture

### Current data flow

```text
Schwarz leaflets API
    ↓
LidlLeafletClient.discover() / fetch_flyer_meta()
    ↓
FlyerMeta in memory
    ↓
ingest.py::ingest_flyer()
    ↓
PDF download and SHA-256 content hash
    ├── R2 flyer PDF: flyers/{year}/{month}/{content_hash}.pdf
    ├── PDF extraction with PyMuPDF
    └── Product card extraction and parsing
            ├── R2 extraction JSON: *.cards.json
            ├── Product image extraction and upload
            └── PostgreSQL product_cards rows
```

### Backend

The Python code is an ingestion application, not an HTTP backend. It contains:

- Schwarz leaflet acquisition in `ingestion/src/lidl_tracker/acquisition.py`.
- PDF extraction in `pdf_extract.py`.
- Spatial card grouping in `cards.py`.
- Deterministic field parsing in `parsers.py`.
- Product image extraction in `product_images.py`.
- PostgreSQL persistence in `storage/database.py`.
- R2-compatible object storage in `storage/r2.py`.
- CLI entry points such as `cli_ingest.py`, `cli_extract.py`, and `cli_watch.py`.
- GitHub Actions for weekly ingestion, product watching, and tests.

There is no FastAPI, Flask, Django, or other HTTP layer. There are no read queries for frontend use. The database module currently exposes only ingestion-oriented functions:

- `apply_migrations()`
- `get_flyer_by_hash()`
- `get_flyer_by_url()`
- `insert_flyer()`
- `update_flyer_status()`
- `upsert_product_cards()`

### Frontend

The Next.js app is under `apps/web` and uses Next.js `16.3.4`, React `19.2.8`, the App Router, and Tailwind CSS v4.

Routes currently implemented:

- `/`: Product Explorer. There is currently no `/products` index route.
- `/products/[slug]`: Product Detail.
- `/flyers`: Flyer Archive.
- `/flyers/[slug]`: Flyer Detail.

All pages and presentation components are server components except `MainNav`, which is a client component for pathname-aware navigation. There is no `fetch`, API client, SWR, React Query, server action, or Next route handler.

The page-level data-access seam is already appropriate for integration:

- `src/lib/flyers/index.ts` exports flyer types, mock accessors, and formatters.
- `src/lib/products/index.ts` exports product types, mock accessors, detail accessors, and formatters.
- Pages call accessors and pass plain typed data to components.
- Components do not import mock data directly.

## 2. Current Data Model

### `flyers`

Defined in `migrations/001_create_flyers.sql` and duplicated as inline SQL in `storage/database.py`.

| Column | Type | Meaning |
| --- | --- | --- |
| `id` | `SERIAL PRIMARY KEY` | Internal flyer identifier |
| `source_url` | `TEXT UNIQUE NOT NULL` | Source PDF URL |
| `storage_key` | `TEXT NOT NULL` | R2 PDF object key |
| `category` | `TEXT NOT NULL DEFAULT ''` | Flyer category |
| `name` | `TEXT NOT NULL DEFAULT ''` | Flyer name |
| `start_date` | `TEXT` | Flyer start date; not a SQL `DATE` |
| `end_date` | `TEXT` | Flyer end date; not a SQL `DATE` |
| `content_hash` | `TEXT UNIQUE NOT NULL` | SHA-256 PDF content hash |
| `downloaded_at` | `TIMESTAMPTZ` | Download timestamp |
| `created_at` | `TIMESTAMPTZ NOT NULL` | Persistence timestamp |
| `status` | `TEXT NOT NULL DEFAULT 'DISCOVERED'` | Ingestion status |
| `slug` | `TEXT` | Nullable persisted flyer slug, added by migration 004 |

Indexes and constraints:

- Unique `content_hash` constraint.
- Unique `source_url` constraint.
- `flyers_status_idx` on `status`.
- Partial unique `flyers_slug_unique` index on non-null `slug`.

Older flyers may have a null slug until `backfill_flyer_slugs()` is run.

### `product_cards`

Defined in `migrations/002_create_product_cards.sql` and extended by migration 003.

| Column | Type | Meaning |
| --- | --- | --- |
| `id` | `BIGSERIAL PRIMARY KEY` | Card identifier |
| `flyer_id` | `INTEGER NOT NULL` | FK to `flyers(id)` with `ON DELETE CASCADE` |
| `card_hash` | `TEXT NOT NULL` | Content hash of one extracted card |
| `card_index` | `INTEGER NOT NULL` | Card order in the flyer |
| `page` | `INTEGER` | PDF page |
| `bbox` | `JSONB` | Card bounding box |
| `raw_text` | `TEXT` | Extracted raw text |
| `brand` | `TEXT` | Parsed brand |
| `name` | `TEXT` | Parsed product name |
| `description` | `TEXT` | Parsed description |
| `quantity` | `JSONB` | Parsed quantity |
| `price` | `DOUBLE PRECISION` | Current flyer price |
| `reference_price` | `DOUBLE PRECISION` | Reference or previous price |
| `unit_prices` | `JSONB` | Unit price values |
| `discount_percent` | `INTEGER` | Discount percentage |
| `lidl_plus` | `BOOLEAN` | Lidl Plus offer flag |
| `currency` | `TEXT` | Defaults to `EUR` |
| `status` | `TEXT` | `ok`, `partial`, or `failed` |
| `parser_version` | `TEXT` | Current parser version is `0.1.0` |
| `warnings` | `JSONB` | Parser warnings |
| `notes` | `JSONB` | Parser notes |
| `payload` | `JSONB NOT NULL` | Complete extracted card payload |
| `image_object_key` | `TEXT` | R2 image object key |
| `image_content_type` | `TEXT` | Image MIME type |
| `image_width` | `INTEGER` | Image width |
| `image_height` | `INTEGER` | Image height |
| `created_at` | `TIMESTAMPTZ` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | Last update timestamp |

Indexes and constraints:

- Foreign key `product_cards.flyer_id → flyers.id` with cascade deletion.
- Unique `(flyer_id, parser_version, card_hash)` constraint.
- `product_cards_flyer_idx` on `flyer_id`.
- `product_cards_name_idx` on `name`.
- `product_cards_parser_idx` on `parser_version`.

### Flyer → product relationship verdict

The database already represents:

```text
flyer
  └── product_cards
```

The relationship is persisted and enforced by a foreign key. A per-flyer product query is therefore possible without a schema redesign.

What does not exist is a canonical product entity:

- There is no `products` table.
- There is no product foreign key on `product_cards`.
- `card_hash` identifies an extracted card within a flyer, not a product across flyers.
- Entity resolution and appearance history are explicitly not implemented.
- `normalized_name` exists inside the card payload but is not a dedicated column.

### Migration behavior and schema version

The checked-in ordered SQL migrations 001–004 define schema version 4: base
flyer and product-card tables/indexes, four image metadata columns on
`product_cards` (003), and the nullable flyer slug plus partial unique index
(004). There is no applied-version history table. `apply_migrations()` uses
repeatable inline DDL; it now uses `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
for all four image columns, matching migration 003. It already performs the
equivalent additive operations for migration 004. Reapplying these changes
does not replace tables or delete flyer, card, or payload data.

`CREATE TABLE IF NOT EXISTS` in migrations 001–002 does not reconcile columns
or constraints on a same-named existing table. The automated additive
upgrades cover installations with the expected 001–002 base schema; partial
or non-standard base schemas still require explicit, data-aware inspection.
Migrations are invoked by ingestion `--migrate`, not automatically by API
startup.

Migration tests cover fresh initialization, repeat application, and upgrading
a legacy schema while checking existing flyer/card data and JSON payload
remain intact. On 2026-10-11, focused parser, CLI, database collection, and
API tests reported 50 passed and 11 skipped. PostgreSQL integration tests
were skipped because no test database was reachable; a disposable Docker
database could not start because the Docker daemon was unavailable. Before
production rollout, inspect the Render database read-only, apply migrations
through the approved process, then verify columns, constraints/indexes,
relationships, and existing records.

## 3. Frontend Data Requirements

### Flyer types

`apps/web/src/lib/flyers/types.ts` defines:

```ts
export interface FlyerArchiveItem {
  id: string;
  slug: string;
  title: string;
  dateFrom: string;
  dateTo: string;
  productCount: number;
  coverImage: string;
  isCurrent?: boolean;
}
```

`coverImage` is currently a hex tint used to render placeholder SVG artwork, not a remote image URL.

### Product types

`apps/web/src/lib/products/types.ts` defines:

```ts
export type ProductCategory =
  | "Dairy" | "Bakery" | "Meat & Fish" | "Fruit & Veg"
  | "Pantry" | "Drinks" | "Frozen" | "Household";

export interface Product {
  id: string;
  slug: string;
  brand: string;
  name: string;
  quantity: string;
  price: number;
  category: ProductCategory;
  lastSeen: string;
  imageUrl: string | null;
  image: {
    shape: PackagingShape;
    tint: string;
  };
}

export interface ProductAppearance {
  date: string;
  price: number;
  flyerId: string;
  flyerName: string;
}

export interface PriceHistoryPoint {
  date: string;
  price: number;
}

export interface ProductDetail extends Product {
  firstSeen: string;
  appearanceCount: number;
  appearances: ProductAppearance[];
  priceHistory: PriceHistoryPoint[];
  referencePrice: number | null;
}
```

### Route-to-data mapping

| Route | Required data | Current source | Backend source | Main gap |
| --- | --- | --- | --- | --- |
| `/` | `Product[]` | `getProducts()` mock | Grouped `product_cards` | Product identity, category, slug |
| `/` | Categories and brands | Mock accessors | Brands from cards; no category source | Category is not in backend |
| `/products/[slug]` | `ProductDetail` | Synthesized mock detail | Grouped cards joined to flyers | Grouping and historical aggregation |
| `/flyers` | Flyer list | Mock accessors | `flyers` plus card counts | Persisted slug required |
| `/flyers/[slug]` | Flyer metadata | Mock accessor | `flyers` | Persisted slug required |
| `/flyers/[slug]` | Products in flyer | Placeholder | `product_cards WHERE flyer_id = ?` | API and UI wiring only |

### Important mismatches

1. Mock flyer routes use `semana-37-2026`, while backend acquisition slugs resemble `folleto-alimentacion-17-8-17-8-26-23-8-26-a07bd0` and are not persisted.
2. The mock data assumes one flyer per week, while the backend has multiple categories such as ALIMENTACIÓN and BAZAR for the same period.
3. Mock products have a stable product identity; backend rows are flyer-specific observations.
4. `Product.category` has no backend source.
5. Product images have R2 object keys in the backend but no URLs.
6. Flyer cover images do not exist in R2; the frontend currently uses generated tint artwork.
7. Product search, filters, and sorting controls are presentational placeholders and are not functional yet.

## 4. Recommended API Boundary

Introduce a read-oriented FastAPI service under `apps/api`. It should depend on the existing `lidl_tracker` package and reuse the existing database and R2 conventions.

### Initial endpoints

```text
GET /v1/flyers
GET /v1/flyers/{slug}
GET /v1/flyers/{slug}/products

GET /v1/products
GET /v1/products/{slug}
```

Also add:

```text
GET /health
```

### Endpoint design

- Use a `/v1` prefix from the beginning.
- Use direct resource responses for detail endpoints.
- Use `{items, total, page, page_size}` for list endpoints so pagination can be introduced without changing the shape later.
- Return HTTP 404 for unknown flyer/product slugs.
- Use FastAPI's standard validation errors for invalid query parameters.
- Return a consistent `{"detail": "..."}` error body for application errors.
- Sort flyers by `start_date` descending.
- Sort derived products by `lastSeen` descending.
- Add `year` filtering for flyers because the existing frontend uses it.
- Defer product search, category filtering, price filtering, and custom sorting until the frontend controls are wired.

### Suggested response responsibilities

The API should return frontend-oriented fields rather than exposing raw database rows:

- Convert database dates to ISO `YYYY-MM-DD` strings.
- Convert JSON quantity values into the frontend's display string.
- Return `imageUrl: null` when no image exists.
- Return a stable API flyer `id` and a routable `slug`.
- Return `ProductAppearance` rows most recent first.
- Return price history oldest first.
- Avoid exposing raw parser payload, bounding boxes, or internal card hashes unless a future diagnostic endpoint needs them.

## 5. Product Identity Strategy

### V1: derive products from cards

For the first integration, derive a product group from:

```text
brand + normalized_name
```

The API can read `payload->>'normalized_name'` and fall back to normalizing `name` when the payload does not contain it.

The derived product contains:

- A deterministic ID derived from the grouping key.
- A deterministic slug generated from brand and normalized name.
- The latest card price.
- The latest flyer date as `lastSeen`.
- The earliest flyer date as `firstSeen`.
- All matching cards as appearances.
- The card prices as price history.
- The highest meaningful reference price.

This avoids an immediate schema change and supports the current Product Detail UI. It has known limitations:

- Product name variants may split one real-world product into multiple groups.
- Quantity or package changes may create separate groups.
- Slugs can change if the grouping inputs change.
- Category cannot be reliably populated from current data.

The API contract must document that derived product slugs are provisional until canonical products are introduced.

### Future canonical model

Do not implement this in the first integration, but leave room for:

```text
products
  id
  slug UNIQUE
  brand
  normalized_name
  display_name
  category
  created_at

product_cards.product_id → products.id
```

The future entity-resolution process would assign cards to canonical products during ingestion. The `/v1/products/{slug}` endpoint can remain unchanged when the source of its data changes.

## 6. Flyer Slugs

Persist a backend-owned flyer slug. The current source URL slug is not persisted and the frontend's week-only slug cannot represent multiple flyers in the same week.

Recommended properties:

- Deterministic.
- URL-safe.
- Unique.
- Based on flyer name/category, date, and a short content-hash suffix.
- Independent from mutable display text where possible.

Example conceptual format:

```text
alimentacion-2026-08-17-a07bd0
```

The exact rule should be documented before implementation. Add a unique `flyers.slug` column and backfill existing rows with a collision-safe rule. Update both:

- The documentary SQL migration files.
- The inline schema in `storage/database.py::apply_migrations()`.

Populate the slug during ingestion so newly inserted rows always have one.

## 7. Images and R2

### Existing storage

R2 object keys currently use:

- Flyer PDFs: `flyers/{year}/{month}/{content_hash}.pdf`
- Extraction JSON: corresponding `.cards.json`
- Product images: `cards/{flyer_id}/Cards/{card_id}/product-image.{ext}`

Only keys are persisted. There is no public URL builder or presigned URL implementation.

### Recommendation

Use public, cacheable asset URLs if the bucket can safely expose published flyer imagery. The API should translate object keys into URLs using a configurable asset base URL.

Recommended order:

1. Public R2/custom asset domain and stable URLs.
2. Presigned GET URLs if the bucket must remain private.
3. Avoid an application image proxy unless authentication or access control later requires it.

The product response should include:

- `imageUrl`.
- `imageWidth`.
- `imageHeight`.

The frontend can then update `ProductImage.tsx`, which is already the isolated image-rendering seam, to use `next/image` when `imageUrl` exists and retain the generated SVG fallback otherwise.

Add the asset host to `images.remotePatterns` in `apps/web/next.config.ts` when remote images are enabled.

Flyer PDFs should remain out of the first UI integration. Later, a flyer `pdfUrl` can be added for a direct “View original PDF” link. Avoid proxying PDFs through the API.

## 8. Local Development and Deployment

### Intended topology

```text
Next.js localhost:3000 or Vercel
        ↓ server-side fetch
FastAPI localhost:8000 or hosted API
        ├── PostgreSQL localhost:5432 or Neon
        └── MinIO localhost:9000 or Cloudflare R2
```

### Environment variables

Add a server-only frontend variable:

```text
LIDL_API_BASE_URL=http://localhost:8000
```

Do not use `NEXT_PUBLIC_` because the current integration should fetch from server components. Configure the value separately for local, Vercel preview, and production environments.

The API should have its existing database and R2 variables plus an asset-base configuration, for example:

```text
API_PUBLIC_ASSET_BASE_URL=http://localhost:9000/lidl-dev
```

The exact production value depends on the final R2 public/custom domain decision.

### CORS

CORS is not required if the browser never calls FastAPI directly. Next.js server components call the API server-to-server. Add CORS only if client-side fetching is introduced later.

### Flyer archive and detail integration (Phase 2)

The Next.js Flyer Archive and Flyer Detail routes use server-side requests to:

- `GET /v1/flyers` — `{items, total, page, page_size}`, with optional `year`, `page`, and `page_size` query parameters.
- `GET /v1/flyers/{slug}` — one flyer summary.

Each summary currently contains `id` (integer), `slug`, `name`, `category`, nullable `start_date`/`end_date`, `status`, and `product_count`. The frontend maps `id` to a string, `name` to `title` (falling back to `category` only when the name is blank), dates to `dateFrom`/`dateTo` (null becomes empty), and `product_count` to `productCount`; `slug` passes through unchanged. `status` is not currently displayed. It reads all list pages (up to the API's 100-item page maximum) so the current flyer and year filters use the complete result set. The archive does not currently offer page navigation.

The web deployment must set the server-only `LIDL_API_BASE_URL` to the API origin; do not expose it as `NEXT_PUBLIC_*`. Since the browser does not call FastAPI, no CORS configuration is needed.

These endpoints do not return flyer cover artwork, a PDF URL, or a per-flyer product listing. The flyer cover tint is a generated visual placeholder, and the detail page explicitly leaves the product section as unavailable; neither should be presented as API data. The detail page only displays fields available from the summary and omits the prior static region label.

### Proxying

Do not add a Next.js rewrite or proxy initially. Direct server-side requests to `LIDL_API_BASE_URL` are simpler and keep the boundary explicit. A rewrite can be added later if local browser-facing API paths become useful.

### Local flow

```text
docker compose up -d
run ingestion against local PostgreSQL and MinIO
start FastAPI on :8000
start Next.js on :3000 with LIDL_API_BASE_URL
```

### Preview environments

Use a shared backend staging environment initially:

```text
Pull request
  ├── Vercel preview → staging API
  └── API tests / staging deployment
```

Do not build per-PR ephemeral databases or APIs yet. Add a dedicated backend deployment once the API has real consumers. The API hosting provider is still an open infrastructure decision.

## 9. Mock-to-Real Migration

The existing page-to-accessor boundary should be preserved.

Recommended structure:

```text
UI components
      ↓
page-level data accessors
      ↓
API implementation or mock implementation
```

### Minimal frontend refactor

1. Add API-backed accessor modules beside the existing mock modules.
2. Keep the existing exported accessor names where possible.
3. Convert accessors to async functions as needed.
4. Keep API-to-frontend mapping in the data-access layer, not in presentation components.
5. Preserve existing component prop types initially.
6. For the Phase 2 flyer routes, require `LIDL_API_BASE_URL` and surface API failures rather than silently falling back to mock flyers. Routes not yet integrated may continue using their existing mock data.

Pages that become async:

- `src/app/page.tsx`.
- `src/app/products/[slug]/page.tsx`.
- Existing flyer pages are already async.

Dynamic route generation needs a decision. Since data changes weekly and the API will be the source of truth, prefer dynamic rendering with appropriate fetch revalidation rather than eagerly generating every product and flyer route. If static generation is retained, make `generateStaticParams()` asynchronous and source slugs from the API.

### Migration order

1. Flyers list.
2. Flyer detail metadata.
3. Flyer products.
4. Products list.
5. Product detail and price history.
6. Product and PDF images.

This order enables the existing Flyer Detail placeholder to become useful before canonical product identity is solved.

## 10. Backend Gap Inventory

### Already exists

- Flyer ingestion and PDF download.
- PostgreSQL flyer persistence.
- Product card persistence.
- Enforced flyer-to-card foreign key.
- Card prices, quantities, discounts, and parser metadata.
- Product image extraction and R2 upload.
- Flyer PDF and extraction JSON R2 storage.
- Local PostgreSQL and MinIO via Docker Compose.
- Existing ingestion tests and GitHub Actions.
- Frontend data-access seams and fallback image representations.

### Small changes

- Add read queries to `storage/database.py`.
- Add and populate a persisted flyer slug.
- Add the FastAPI application and Pydantic response models.
- Add API query and service tests.
- Add API asset URL construction.
- Normalize dates at the API boundary.
- Add `LIDL_API_BASE_URL` to frontend configuration.
- Replace mock accessor bodies with API-backed implementations.
- Replace the Flyer Detail placeholder with real per-flyer cards.
- Configure Next.js remote image hosts when images are exposed.
- Add direct database-layer tests; currently none exist.

### Architectural changes

- Canonical `products` table and entity-resolution process.
- Product category classification.
- Flyer cover-image extraction and storage.
- API hosting and deployment pipeline.
- Connection pooling if API traffic grows beyond the initial scale.

### Future, not part of the first integration

- Authentication and user accounts.
- Web-managed watch lists.
- Search/filter/sort behavior beyond current UI requirements.
- PDF viewer.
- Shopping lists.
- Recurrence prediction.
- Multi-region support.
- Redis or other external caching.
- Per-PR ephemeral backend environments.

## 11. Implementation Sequence

### Phase 0 — API contract and identifier decisions

**Files likely to change**

- New `docs/api.md`.

**Database changes**

- None.

**API changes**

- Define response shapes, slug rules, error format, pagination, and versioning.

**Frontend changes**

- None.

**Tests**

- None beyond validating the written contract.

**Dependencies and risks**

- The flyer slug rule and derived product slug rule must be decided before implementation.
- Confirm R2 public/private posture before choosing URL behavior.

### Phase 1 — API foundation and flyer reads

**Files likely to change**

- New `apps/api/` application.
- `ingestion/src/lidl_tracker/storage/database.py`.
- `ingestion/src/lidl_tracker/ingest.py`.
- New migration 004.
- `.env.example`.
- Root `README.md`.

**Database changes**

- Add unique `flyers.slug`.
- Backfill existing rows.
- Populate slugs during ingestion.
- Update inline schema and documentary migration files together.

**API changes**

- Add `/health`.
- Add `GET /v1/flyers`.
- Add `GET /v1/flyers/{slug}`.

**Frontend changes**

- None initially, or add the API client seam without switching pages yet.

**Tests required**

- Direct database query tests.
- Slug determinism and collision tests.
- FastAPI router tests with mocked persistence.

**Risks**

- Existing flyer names and dates may produce slug collisions; use a short content-hash suffix.
- Schema exists in both inline Python and SQL files; both must remain synchronized.

### Phase 2 — Flyers frontend

**Files likely to change**

- `apps/web/src/lib/flyers/api.ts`.
- `apps/web/src/lib/flyers/index.ts`.
- `apps/web/src/app/flyers/page.tsx`.
- `apps/web/src/app/flyers/[slug]/page.tsx`.

**Database changes**

- None beyond Phase 1.

**API changes**

- None beyond Phase 1.

**Frontend changes**

- Add API-backed flyer accessors and adapters.
- Preserve `FlyerArchiveItem` props for existing components.
- Set `LIDL_API_BASE_URL`.
- Decide whether dynamic routes replace `generateStaticParams()`.

**Tests required**

- API response adapter tests.
- Flyer date and year-filter tests.
- Lint and production build.

**Risks**

- Multiple flyers can share a week; do not collapse them into one week-only identity.

### Phase 3 — Flyer products

**Status (2026-10-12): per-flyer cards API implemented; frontend integration
remains deferred.** The audited production schema and card-version findings
provided for this phase match the checked-in model. The API serves cards from
the parser version deployed with the service (currently `0.1.0`) and keeps
other parser versions separate. The Render service is documented to use Neon
through `DATABASE_URL`, but this workspace has no Render service binding or
Render API credentials with which to verify that its live Neon branch matches
the audited database.

#### Implemented endpoint

```text
GET /v1/flyers/{slug}/products?page=1&page_size=20
```

Use the existing list envelope, with `page >= 1` and
`1 <= page_size <= 100` (the current flyer list's default and maximum).
`items` contains flyer-specific persisted card observations, not canonical
products. The endpoint selects only the parser version deployed with the API
(`lidl_tracker.parsers.PARSER_VERSION`); it does not combine older versions.
Within that version it returns all statuses, including `partial` cards with
warnings and `failed` cards missing required name or price. `total` counts
cards in that selected version. Order is stable by `card_index ASC, id ASC`;
`card_index` is assigned from zero by the persistence code. An empty known
flyer returns HTTP 200 with `items: []` and `total: 0`; a page past the end
also returns an empty `items` array with the unchanged total. An unknown
flyer slug returns HTTP 404, not an empty page. Query validation follows the
flyer list route: `page >= 1`, `1 <= page_size <= 100`, default page size 20.

The following illustrative response uses only fields represented by the
current extraction/storage model. Values are examples, not claims about a
particular persisted card:

```json
{
  "items": [
    {
      "id": "314",
      "card_index": 0,
      "page": 1,
      "brand": "CHEF SELECT",
      "name": "Guacamole",
      "description": "96% aguacate.",
      "quantity": {
        "value": 500.0,
        "unit": "g",
        "count": null,
        "total": 500.0,
        "approximate": false,
        "values": [],
        "raw": "500 g"
      },
      "price": 3.75,
      "reference_price": null,
      "unit_prices": [
        {
          "value": 7.5,
          "unit": "kg",
          "basis": 1,
          "per_unit": 7.5,
          "raw": "7,50 €/kg"
        }
      ],
      "discount_percent": null,
      "lidl_plus": false,
      "currency": "EUR",
      "status": "ok",
      "parser_version": "0.1.0",
      "warnings": [],
      "notes": ["no_unit_price"]
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

Card `id` is the `product_cards.id`, serialized as a decimal string because
the column is `BIGSERIAL` and JavaScript numbers cannot exactly represent all
64-bit integers; `parser_version` identifies the selected extraction;
`page` is the source PDF page and may be null. `brand`,
`name`, `description`, `quantity`, `price`, and
`reference_price` may be null. Preserve the parsed quantity object and its
`raw` source text rather than guessing a display quantity from `value`,
`count`, or `unit`; the parser also represents approximate, multi-size, and
unit-only quantities. `unit_prices` is a JSON array (empty when absent) with
`value`, `unit`, `basis`, `per_unit`, and `raw`. Preserve `price` as nullable
numeric data and `currency` as stored (defaulted to `EUR` by ingestion), not
as a fabricated zero. Promotional facts are `discount_percent` (nullable)
and `lidl_plus` (boolean); `reference_price` is a separate nullable value and
must not be given a stronger “was”/“save” interpretation without confirming
its source semantics. `status` currently uses `ok`, `partial`, or `failed`;
`warnings` and `notes` are string arrays. These are parser fields, not
frontend promotion labels.

Do not return parser payload, `raw_text`, card hashes, bounding boxes, or R2
object keys in this UI endpoint. The current schema has image object keys and
dimensions, but no public asset URL builder; omit image URLs for now and use
a neutral artwork placeholder. No product category, canonical product slug,
or product identity is stored on a card. Do not synthesize these in the API.
The UI should omit a missing brand, show a neutral “name unavailable” state
for a missing name, and show a “price unavailable” state rather than sending
null to `formatPrice`. Show promotion details only when their stored facts
are present/true. Prefer a flyer-specific card presentation over reusing
`ProductCard` unchanged: it requires non-null `brand`, `name`, `quantity`,
`price`, a mock-only category and packaging artwork, and a `/products/{slug}`
link, none of which is a complete contract for an extracted card.

#### Storage relationship and query path

The canonical persisted relationship is
`product_cards.flyer_id -> flyers.id`, enforced by a foreign key with
`ON DELETE CASCADE`. The requested route resolves its URL slug using
`db.get_flyer_by_slug(slug)`, which returns the persisted flyer record and its
card count (or `None`). If no record or no persisted slug matches, return 404.
Use the returned integer flyer ID to select that flyer's card rows; never
look up cards by the slug string, use a week-only identifier, or infer the
relationship from product names. A new query helper should return a page of
cards and an unpaged count for that flyer, using bound parameters and the
stable ordering above. Keep the read logic in the existing database module
or extract it only if the router begins to grow.

The route resolves the persisted slug with `db.get_flyer_by_slug()` and passes
the returned flyer ID and active parser version to
`db.list_product_cards()`. The database helper uses bound parameters for both
the page query and count, and orders by `card_index, id`. The response omits
payload, raw text, hashes, bounding boxes, and stored image metadata because
there is no public image URL contract. `ProductCard.to_dict()` in `cards.py`
emits the parsed quantity and unit-price structures;
`ingest._persist_extraction()` adds the content hash and image metadata and
calls the upsert.

#### Migration and deployed-schema findings

The repository's final intended schema is split across migrations:

- `001_create_flyers.sql`: `flyers`.
- `002_create_product_cards.sql`: `product_cards`, its flyer FK, unique
  `(flyer_id, parser_version, card_hash)`, and indexes.
- `003_add_product_card_image.sql`: four image metadata columns.
- `004_add_flyer_slug.sql`: nullable `flyers.slug` and a partial unique index.

Schema version 4 is represented by the ordered SQL files 001–004; there is
no `schema_migrations` table or applied-version ledger. The existing
architecture applies repeatable DDL rather than recording executions.
`storage.database.apply_migrations()` keeps the runtime DDL inline. It now
adds the four nullable image columns with `ADD COLUMN IF NOT EXISTS` (matching
migration 003), and already adds nullable `flyers.slug` and its partial unique
index (matching migration 004). These changes are safe to repeat and preserve
existing flyer/card rows and JSON payloads. Migration 003 was the identified
runtime gap; migration 004 was already covered.

`CREATE TABLE IF NOT EXISTS` in migrations 001 and 002 does not reconcile
columns, primary/foreign keys, or unique constraints when a table of the same
name already exists. The separately declared indexes are attempted on every
run, but the routine does not rebuild an incompatible or partially created
base table. Existing installations that were created from migrations 001
and 002 are covered by the additive 003/004 operations; a partial or
non-standard base schema still needs read-only inspection and an explicit,
data-aware repair rather than an automatic constraint rebuild.

The ingestion workflow invokes `cli_ingest --migrate`, which calls this inline
routine and backfills null flyer slugs; the API Render service does not run
migrations at startup. Schema migration and slug backfill therefore remain
an explicit deployment/ingestion operation, not an API startup side effect.

**Migration verification (2026-10-11):** API and parser tests passed
(`50 passed` across `apps/api/tests`, `ingestion/tests/test_cli_ingest.py`,
`ingestion/tests/test_parsers.py`, and database test collection; `11`
PostgreSQL tests skipped because no test
server was reachable). Fresh-schema, repeat-application, and legacy-schema
upgrade cases are covered by isolated-schema PostgreSQL tests, but could not
be executed here: the disposable Docker attempt was blocked because the
Docker daemon is not running. A wider ingestion/API run also encountered
unrelated Windows temporary-directory access and PDF-file-lock failures.
`compileall` passed for the modified Python modules. No Python lint or
type-check command is configured.

The PostgreSQL migration tests use a uniquely named temporary schema under
`TEST_DATABASE_URL`; they do not truncate shared tables. They never inherit
`DATABASE_URL`, and their default is local `lidl_test`. In this phase, the
PostgreSQL integration tests were skipped because no local test server was
available. No production connection, migration, or data mutation was
attempted. The supplied audit did not include a null-slug/backfill count, so
verify that separately before relying on slug resolution for every flyer.

The production inspection supplied for this phase confirmed the unique
partial `flyers.slug` index, the four card-image metadata columns, the
`product_cards.flyer_id -> flyers.id ON DELETE CASCADE` foreign key, and the
unique `(flyer_id, parser_version, card_hash)` constraint. It found 1,409
cards across nine flyers, all on parser version `0.1.0`, including both `ok`
and `partial` statuses. This implementation uses those findings; it did not
connect to or mutate production. The inspection did not establish the live
Render service's configured `DATABASE_URL` value or Neon branch. Deployment
documentation specifies Neon via `DATABASE_URL` and no separate branch, so
the intended target is the audited Neon database; its actual live binding
remains unverified from this workspace.

The uniqueness key permits multiple parser versions to coexist, and
`card_index` is not constrained unique. This API intentionally selects only
the parser version deployed with the API and counts/orders rows within that
version; it does not merge historical versions or deduplicate by index. The
audited production data currently has only `0.1.0`. If a parser version is
upgraded, flyers without rows for that version will return an empty selected
set until re-extracted. The flyer summary's existing `product_count` still
counts all persisted versions, so those counts could differ if historical
versions are later retained alongside current rows.

#### Flyer cards versus Product Explorer products

A flyer card is one extraction observation tied to exactly one flyer and
identified by its card-row ID. The Product Explorer's mock `Product` is a
different, cross-flyer concept: it requires a slug, category, required price,
and product identity. The extraction payload contains `normalized_name`
inside the `product_cards.payload` JSONB column (it is not a dedicated
column), and `parsers.normalize_name()` can support the previously proposed
provisional grouping key `(brand, normalized_name)` for a future derived
product API.
That grouping is not a persisted FK or canonical identity: it can split
variants and cannot provide the mock category. Keep Phase 3 cards flyer-scoped
and do not link them to `/products/{slug}` until a distinct product mapping
exists. Deriving Product Explorer groups remains Phase 4.

#### Recommended implementation order / blockers

1. The API query, response schemas, route, and mocked API contract tests are
   implemented. The production findings supplied for this phase confirm the
   persisted fields and a single parser version; historical versions remain
   excluded rather than merged into the response.
2. The deployment documentation identifies the Render service and its
   `DATABASE_URL`-to-Neon configuration, but its live database/branch binding
   and API origin could not be verified from this workspace.
3. Frontend API access and flyer-specific card rendering remain a separate
   implementation task. Keep these observations separate from canonical
   products; fetch/paginate the API from the server and display missing
   values without inventing image URLs.
4. Validate empty/loading/error states, optional values, and that every
   rendered card came from the selected flyer. Keep image placeholders until
   an asset URL contract exists.

**Risks**

- Images may remain unavailable until Phase 5; preserve the existing placeholder path.

### Phase 4 — Derived Products API

**Files likely to change**

- `apps/api/routers/products.py`.
- New product grouping/service module.
- `apps/web/src/lib/products/api.ts`.
- `apps/web/src/lib/products/index.ts`.
- `apps/web/src/app/page.tsx`.
- `apps/web/src/app/products/[slug]/page.tsx`.

**Database changes**

- None.
- Consider an expression index on `payload->>'normalized_name'` only if query performance requires it.

**API changes**

- Add `GET /v1/products`.
- Add `GET /v1/products/{slug}`.
- Group cards by brand and normalized name.
- Return appearances and price history in the frontend's expected order.

**Frontend changes**

- Replace synthesized PRNG details with API data.
- Preserve component-facing `Product` and `ProductDetail` shapes where possible.
- Treat category as unavailable until a real source exists.

**Tests required**

- Cross-flyer grouping tests.
- Derived slug stability tests.
- Price-history ordering tests.
- First/last-seen aggregation tests.
- Frontend adapter tests.

**Risks**

- Product name variants can split one real-world product into separate derived products.
- Derived slugs are provisional until canonical products exist.

### Phase 5 — Images and assets

**Files likely to change**

- API asset URL configuration and serializers.
- `apps/web/next.config.ts`.
- `apps/web/src/components/products/ProductImage.tsx`.
- Local MinIO initialization/configuration if public downloads are required.

**Database changes**

- None; image columns already exist.

**API changes**

- Return `imageUrl`, width, and height.

**Frontend changes**

- Use `next/image` for available remote images.
- Retain generated SVG fallback for missing images.

**Tests required**

- URL generation tests for local and production environments.
- Missing-image and mixed-format tests.
- Next.js build with remote image configuration.

**Risks**

- Private R2 buckets require presigned URLs instead of stable public URLs.
- Image extraction intentionally allows cards without images.

### Phase 6 — Deployment environments

**Files likely to change**

- API deployment configuration.
- GitHub Actions API test/deploy workflow.
- `watch-test.yml` or a dedicated API test workflow.
- Root README and environment documentation.

**Database changes**

- None.

**API changes**

- Deploy staging and production API environments.

**Frontend changes**

- Configure Vercel preview and production values for `LIDL_API_BASE_URL`.

**Tests required**

- API unit/integration suite in CI.
- Frontend build against a staging API or contract fixture.
- Smoke test for Vercel preview → staging API connectivity.

**Risks**

- Neon connection limits if each request creates a new connection.
- Secret management across GitHub, Vercel, API hosting, Neon, and R2.
- Production API hosting provider is not yet selected.

## Final Recommendation

The smallest production-oriented path is:

1. Persist a real flyer slug.
2. Add read queries to the existing Python database module.
3. Add a thin FastAPI read API under `apps/api`.
4. Expose flyer metadata and the existing flyer-to-card relationship first.
5. Derive products from card observations for the initial Product Explorer and Product Detail integration.
6. Keep canonical product entity resolution, categories, PDF viewing, authentication, and advanced search explicitly out of scope.
7. Replace mocks through the existing data-access seams rather than rewriting UI components.

This preserves the existing ingestion architecture, uses the relationship already present in PostgreSQL, and provides a path from the current deterministic mocks to real production data without prematurely redesigning product identity.
