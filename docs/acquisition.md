# Lidl Spain flyer acquisition — reverse-engineering result

Everything below was **captured from real network traffic**, not guessed.
Reproduce with `python tools/capture_network.py`.

## Summary

Lidl Spain does use Schwarz Group's leaflet infrastructure. The flyer page
is server-rendered via ESI (`esi.leaflets.schwarz`), the viewer is a SPA
(`lidl.leaflets.schwarz`), and metadata comes from a public JSON API. PDFs
are served directly from `assets.leaflets.schwarz`.

**No browser is needed in production.** Two plain HTTP GETs are enough.

## The critical detail

The `client_locale` parameter is **not** `es_ES` or `es-ES`. It is:

```
client_locale=lidl/es-ES
```

Every other format returns HTTP 400 with
`"The request contains some filter attributes with wrongly formatted values"`.
This is why guessing the endpoint failed and traffic capture was required.

## Endpoints

### Overview (all current flyers + direct PDF URLs)

```
GET https://endpoints.leaflets.schwarz/v4/overview
    ?client_locale=lidl/es-ES
    &region_id=0
```

Response shape:

```
categories[]                     e.g. "Folletos"
  subcategories[]                e.g. "Folletos de Alimentación", "Folletos de Bazar"
    flyers[]
      id                         UUID, e.g. 019fcbac-d0f6-75d2-aba7-0ae8c8b923dd
      name                       "FOLLETO ALIMENTACIÓN 17/8"
      title                      "17/8/26-23/8/26"
      pdfUrl / hiResPdfUrl       direct PDF (no auth, no referer check)
      hiResFileSize / fileSize   bytes — useful for idempotent downloads
      startDate / endDate        publication window
      offerStartDate / offerEndDate   the dates the prices are actually valid
      status                     "current" | ...
      flyerUrlAbsolute           https://www.lidl.es/l/folletos/<slug>/ar/0
      thumbnailUrl / teasers     imgproxy.leaflets.schwarz assets
      regions[]                  [{"type": "national", "code": "0"}]
```

`offerStartDate` / `offerEndDate` are the fields to store as the appearance
window; `startDate` / `endDate` are wider (publication, not validity).

### Single flyer (adds per-page data)

```
GET https://endpoints.leaflets.schwarz/v4/flyer
    ?flyer_identifier=<slug>
    &region_id=0
```

Slug comes from `flyerUrlAbsolute`, e.g.
`folleto-alimentacion-17-8-17-8-26-23-8-26-a07bd0`.

Adds `pages[]` with `number`, `width`, `height` and a `keyWords` string of
the page's text. That `keyWords` field is an independent cross-check
against our own PDF text extraction.

### PDF assets

```
https://assets.leaflets.schwarz/leaflets/pdfs/<flyer-uuid>/<NAME>-00.pdf
```

Plain GET, no authentication. (The `object.storage.eu01.onstackit.cloud`
host mentioned in early notes did not appear in Spanish traffic; the
Spanish market serves via `assets.leaflets.schwarz`.)

## Regionalisation

The overview response reports `isRegionalized`, and flyers carry
`regions: [{"type": "national", "code": "0"}]`. Spanish flyers observed so
far are **national**, so `region_id=0` is sufficient.

## Idempotency

`FlyerMeta.identity_hash` is a SHA-256 prefix of the PDF URL, so a
previously discovered flyer whose asset changes is detectable. Downloads
skip when a local file already matches the advertised `fileSize`, and each
PDF is written with a `.meta.json` sidecar containing the full metadata,
`downloaded_at` and the file's `content_hash`.

## Observed flyers (2026-08-12)

| category | name | offer window | pages | size |
|---|---|---|---|---|
| Alimentación | FOLLETO ALIMENTACIÓN 10/8 | 2026-08-10 → 16 | 67 | 23.4 MB |
| Alimentación | FOLLETO ALIMENTACIÓN 17/8 | 2026-08-17 → 23 | 51 | 23.8 MB |
| Bazar | FOLLETO BAZAR 10/8 | 2026-08-10 → 16 | 23 | 9.2 MB |
| Bazar | FOLLETO BAZAR 17/8 | 2026-08-17 → 23 | 31 | 14.2 MB |

Both the current and the *upcoming* week are exposed, so the crawler sees
new flyers roughly a week before their offers start.
