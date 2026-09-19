"""FastAPI application exposing read-only flyer/product data to the web frontend.

Run locally with:

    uvicorn api.main:app --reload --port 8000

Requires DATABASE_URL to be set (see `lidl_tracker.storage.database`) and
both `ingestion` and `apps/api` installed editable in the same
environment.
"""

from __future__ import annotations

from fastapi import FastAPI

from .routers import flyers, health

app = FastAPI(
    title="Lidl Tracker API",
    version="0.1.0",
    description="Read-only API exposing ingested Lidl flyer data to the web frontend.",
)

app.include_router(health.router)
app.include_router(flyers.router)
