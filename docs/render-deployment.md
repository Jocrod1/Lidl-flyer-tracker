# Render backend deployment

The current deployment is one Render Web Service for the read-only FastAPI
backend:

`main` → Render → `lidl-tracker-api`

The API does not run database migrations at startup and does not run flyer
ingestion. Raw flyers remain in R2 and queryable data remains in Neon
PostgreSQL.

## Current Render service

| Setting | Value |
| --- | --- |
| Service name | `lidl-tracker-api` |
| Repository | `Jocrod1/Lidl-flyer-tracker` |
| Branch | `main` |
| Root directory | `.` |
| Runtime | Python 3 |
| Build command | `pip install ./ingestion ./apps/api` |
| Start command | `python -m api.run` |
| Health check path | `/health` |

The start command uses Uvicorn, binds to `0.0.0.0`, and reads Render's
`PORT` environment variable. If `PORT` is absent locally, it defaults to
`10000`.

## Environment variables

Configure these variables on `lidl-tracker-api`:

| Variable | Required | Secret? | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes | **Yes** | Neon PostgreSQL connection string required by the API. |
| `PORT` | Provided by Render | No | Render injects the listening port; do not hard-code or configure it as a secret. |

The current HTTP API does not access R2, so do not configure
`R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, or
`R2_BUCKET_NAME` on this Render service. Those variables remain ingestion
configuration only. When used by ingestion, `R2_ACCESS_KEY_ID` and
`R2_SECRET_ACCESS_KEY` are secrets; the endpoint and bucket name are not
credentials.

The `/health` endpoint is intentionally lightweight and does not contact Neon
or R2. `/v1/flyers` and `/v1/flyers/{slug}` require the configured database
connection.

## Future PR/Staging deployments

A separate Render Web Service may be added later if PR previews or a dedicated
integration environment become necessary. That would be a future service and
branch decision; it is not part of the current deployment and does not require
creating a `staging` branch now.
