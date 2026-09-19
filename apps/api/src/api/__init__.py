"""Read-only HTTP API exposing ingested Lidl flyer/product data.

This package intentionally has no persistence logic of its own — it
imports and reuses `lidl_tracker.storage.database`, which must be
installed editable in the same environment (see the repository root
README / `apps/api/README.md`).
"""
